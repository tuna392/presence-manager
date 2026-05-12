from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from shared.database import get_db, DBMember, StatusUpdate, DBStatusLog

app = FastAPI()


# ステータスを更新し、同時に履歴（ログ）を残すAPI (POST /api/update)
# iPadの画面でメンバーのカードをタップして、状態を変えた時に呼ばれる
@app.post("/api/update")
def update_status(data: StatusUpdate, db: Session = Depends(get_db)):
    # 1. データベースから、送られてきたIDを持つメンバーを探し出す
    member = db.query(DBMember).filter(DBMember.id == data.id).first()
    
    # もし該当するメンバーがいなかった場合は、エラー（404 Not Found）を返して処理を止める
    if not member: 
        raise HTTPException(status_code=404)

    # 2. 【現在状態の更新】
    # メンバー一覧（lab_members_v2）の現在のステータスと、最終更新時間を最新に書き換える
    member.status = data.status
    member.updated_at = datetime.now()

    # 3. 【履歴（ログ）の保存】※週の滞在時間計算のために超重要！
    # 誰が(member_id)、いつ(timestamp)、何になったか(status)を、履歴テーブル（lab_status_logs）に記録する
    new_log = DBStatusLog(
        member_id=data.id, 
        status=data.status, 
        timestamp=datetime.now()
    )
    db.add(new_log) # 新しい履歴データを追加する準備

    # 4. 【変更の確定】
    # 現在状態の更新と、履歴の追加をセットにして、データベースに完全に保存（セーブ）する
    db.commit()
    
    # 画面側に「無事に更新と記録が終わったよ」と伝える
    return {"message": "Success"}