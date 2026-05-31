from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from shared.database import get_db, DBMember, MemberCreate, MemberReorder, DBStatusLog

app = FastAPI()


# 1. メンバー一覧と「今週の滞在時間」を取得するAPI (GET /api/members)
@app.get("/api/members")
def read_members(db: Session = Depends(get_db)):
    # 登録されているメンバーを表示順（order_index）に並べて全員取得
    members = db.query(DBMember).order_by(DBMember.order_index).all()

    # --- 時差対応と「今週の月曜0時」の計算 ---
    now_utc = datetime.utcnow()
    now_jst = now_utc + timedelta(hours=9)
    days_since_monday = now_jst.weekday()
    start_of_week_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    start_of_week = start_of_week_jst - timedelta(hours=9)
    # ----------------------------------------

    all_member_ids = [m.id for m in members]

    # ★ 修正ポイント: 全員分のログを2回のクエリでまとめて取得（N+1解消）
    all_logs = db.query(DBStatusLog).filter(
        DBStatusLog.member_id.in_(all_member_ids),
        DBStatusLog.timestamp >= start_of_week
    ).order_by(DBStatusLog.timestamp).all()

    all_initial_logs = db.query(DBStatusLog).filter(
        DBStatusLog.member_id.in_(all_member_ids),
        DBStatusLog.timestamp < start_of_week
    ).order_by(DBStatusLog.timestamp.desc()).all()

    # メンバーIDごとに辞書で仕分け
    logs_by_member = defaultdict(list)
    for log in all_logs:
        logs_by_member[log.member_id].append(log)

    # 各メンバーの「週初め時点での最後のログ」を辞書で管理（descで取得済みなので最初の1件が最新）
    initial_log_by_member = {}
    for log in all_initial_logs:
        if log.member_id not in initial_log_by_member:
            initial_log_by_member[log.member_id] = log

    result = []
    for m in members:
        logs = logs_by_member[m.id]
        initial_log = initial_log_by_member.get(m.id)

        total_seconds = 0
        last_active = None

        if initial_log and initial_log.status != "帰宅":
            last_active = start_of_week

        for log in logs:
            if log.status != "帰宅":
                if last_active is None:
                    last_active = log.timestamp
            else:
                if last_active is not None:
                    total_seconds += (log.timestamp - last_active).total_seconds()
                    last_active = None

        if last_active is not None and m.status != "帰宅":
            total_seconds += (now_utc - last_active).total_seconds()

        log_history = [{"status": log.status, "timestamp": log.timestamp.isoformat()} for log in logs]
        log_history.reverse()

        result.append({
            "id": m.id,
            "name": m.name,
            "status": m.status,
            "updated_at": m.updated_at,
            "order_index": m.order_index,
            "weekly_minutes": int(total_seconds // 60),
            "recent_logs": log_history
        })

    return result


# 2. 新しいメンバーを追加するAPI (POST /api/members)
@app.post("/api/members")
def add_member(data: MemberCreate, db: Session = Depends(get_db)):
    members = db.query(DBMember).all()
    max_order = max([m.order_index or 0 for m in members]) if members else 0
    new_member = DBMember(name=data.name, is_admin=data.is_admin, order_index=max_order + 1)
    db.add(new_member)
    db.commit()
    return {"message": "Success"}


# 3. メンバーを削除するAPI (DELETE /api/members)
@app.delete("/api/members")
def remove_member(id: int, db: Session = Depends(get_db)):
    member = db.query(DBMember).filter(DBMember.id == id).first()
    if not member:
        raise HTTPException(status_code=404)
    db.delete(member)
    db.commit()
    return {"message": "Deleted"}


# 4. ドラッグ＆ドロップで順番を入れ替えるAPI (PUT /api/members)
@app.put("/api/members")
def reorder_members(data: MemberReorder, db: Session = Depends(get_db)):
    for index, member_id in enumerate(data.ordered_ids):
        member = db.query(DBMember).filter(DBMember.id == member_id).first()
        if member:
            member.order_index = index
    db.commit()
    return {"message": "Reordered"}