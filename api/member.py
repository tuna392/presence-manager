from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from shared.database import get_db, DBMember, MemberCreate, MemberReorder, DBStatusLog

app = FastAPI()


# 1. メンバー一覧と「今週の滞在時間」を取得するAPI (GET /api/members)
@app.get("/api/members")
def read_members(db: Session = Depends(get_db)):
    # 登録されているメンバーを表示順（order_index）に並べて全員取得
    members = db.query(DBMember).order_by(DBMember.order_index).all()
    
    # --- 時差対応と「今週の月曜0時」の計算 ---
    # Vercelのサーバーはアメリカ時間（UTC）で動いているため、日本時間（JST）への変換が必要
    now_utc = datetime.utcnow()
    now_jst = now_utc + timedelta(hours=9) # 日本時間に変換（+9時間）

    # 日本時間基準で「今週の月曜日」が何日前かを計算（月曜=0, 火曜=1...）
    days_since_monday = now_jst.weekday()
    
    # 日本時間での「今週の月曜日の午前0時ピッタリ」の時間を割り出す
    start_of_week_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)

    # データベースに保存されている記録はUTC（-9時間）なので、検索用にUTCに戻す
    start_of_week = start_of_week_jst - timedelta(hours=9)
    # ----------------------------------------

    result = []
    # 各メンバーごとに、滞在時間の集計を行う
    for m in members:
        # 今週の月曜0時「以降」のステータス変更履歴を古い順に取得
        logs = db.query(DBStatusLog).filter(
            DBStatusLog.member_id == m.id,
            DBStatusLog.timestamp >= start_of_week
        ).order_by(DBStatusLog.timestamp).all()

        # 月曜0時「より前」の最後のログを取得（月曜0時の時点で何だったかを知るため）
        initial_log = db.query(DBStatusLog).filter(
            DBStatusLog.member_id == m.id,
            DBStatusLog.timestamp < start_of_week
        ).order_by(DBStatusLog.timestamp.desc()).first()

        total_seconds = 0  # 滞在時間の合計（秒）
        last_active = None # ストップウォッチの開始時間をメモする変数

        # もし月曜0時の時点で「帰宅以外（＝在席など）」だった場合、月曜0時からストップウォッチを開始
        if initial_log and initial_log.status != "帰宅":
            last_active = start_of_week

        # 取得したログを1つずつ確認して、ストップウォッチを動かす
        for log in logs:
            if log.status != "帰宅":
                # 「帰宅以外」になったらストップウォッチを開始（まだ開始していない場合のみ）
                if last_active is None:
                    last_active = log.timestamp
            else:
                # 「帰宅」になったら、開始時間から今まで何秒経ったかを計算して合計に足す
                if last_active is not None:
                    total_seconds += (log.timestamp - last_active).total_seconds()
                    last_active = None # ストップウォッチを止める

        # すべてのログを見終わった後、今現在も「帰宅以外」なら、現在時刻までの時間を足す
        if last_active is not None and m.status != "帰宅":
            total_seconds += (now_utc - last_active).total_seconds() 

        # 画面に「履歴一覧」も渡してあげる処理
        log_history = []
        for log in logs:
            log_history.append({
                "status": log.status,
                "timestamp": log.timestamp.isoformat() # 時間を文字列に変換
            })
        log_history.reverse() # 最新の記録が一番上に来るように逆順にする

        # フロントエンド（画面）に返すデータを作成
        result.append({
            "id": m.id,
            "name": m.name,
            "status": m.status,
            "updated_at": m.updated_at,
            "order_index": m.order_index,
            "weekly_minutes": int(total_seconds // 60), # 秒を分に直して渡す
            "recent_logs": log_history
            })

    return result



# 2. 新しいメンバーを追加するAPI (POST /api/members)
@app.post("/api/members")
def add_member(data: MemberCreate, db: Session = Depends(get_db)):
    # 今いるメンバーを全員取得
    members = db.query(DBMember).all()
    # 既存メンバーの中で一番大きい順番（一番下）の数字を取得
    max_order = max([m.order_index or 0 for m in members]) if members else 0
    
    # 新しいメンバーを、リストの一番最後（max_order + 1）に追加して保存
    new_member = DBMember(name=data.name, is_admin=data.is_admin, order_index=max_order + 1)
    db.add(new_member)
    db.commit() # データベースに変更を確定
    return {"message": "Success"}


# 3. メンバーを削除するAPI (DELETE /api/members)
@app.delete("/api/members")
def remove_member(id: int, db: Session = Depends(get_db)):
    # 送られてきたIDのメンバーを探す
    member = db.query(DBMember).filter(DBMember.id == id).first()
    # もしいなければエラー（404 Not Found）を返す
    if not member: 
        raise HTTPException(status_code=404)
        
    # 見つかったら削除して保存
    db.delete(member)
    db.commit()
    return {"message": "Deleted"}



# 4. ドラッグ＆ドロップで順番を入れ替えるAPI (PUT /api/members)
@app.put("/api/members")
def reorder_members(data: MemberReorder, db: Session = Depends(get_db)):
    # フロントエンドから「新しい順番のIDリスト」が送られてくる
    # 例: [3, 1, 2] （ID=3の人が1番目、ID=1の人が2番目...）
    for index, member_id in enumerate(data.ordered_ids):
        # 順番にメンバーを検索し、新しい順番（index）を書き込んでいく
        member = db.query(DBMember).filter(DBMember.id == member_id).first()
        if member:
            member.order_index = index
            
    db.commit() # 全員の順番の更新を確定
    return {"message": "Reordered"}