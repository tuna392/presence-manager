from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from shared.database import get_db, DBSettings, SettingUpdate

app = FastAPI()

# 1. システム設定を読み込むAPI (GET /api/settings)
# 画面を開いた時などに、現在の設定データ（ステータス一覧など）を渡す
@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    # データベースの lab_settings_v2 テーブルから、最初の1行（設定）を取り出す
    settings = db.query(DBSettings).first()
    
    # もし設定がまだ存在しない場合（システムを初めて起動した時など）
    if not settings:
        # デフォルトの初期値を作ってデータベースに登録する
        settings = DBSettings(
            id=1, 
            show_duration=True, # 経過時間を表示するかどうか
            status_list="帰宅,在席 2508,7階2721,授業or実習,教員室4413,学内,喫煙,図書館,食事,外出" # 初期ステータス一覧
        )
        db.add(settings) # DBに追加する準備
        db.commit()      # DBに変更を確定（セーブ）
        db.refresh(settings) # 今保存した最新の状態をもう一度読み込み直す
        
    return settings # フロントエンド（画面側）に設定データを渡す



# 2. システム設定を更新（保存）するAPI (POST /api/settings)
# 管理画面（admin.html）から設定を変更した時に呼ばれる
@app.post("/api/settings")
def update_settings(data: SettingUpdate, db: Session = Depends(get_db)):
    # データベースから現在の設定を取り出す
    settings = db.query(DBSettings).first()
    
    # 万が一、設定行が消えてしまっていた場合のセーフティネット
    if not settings:
        settings = DBSettings(id=1)
        db.add(settings)
        
    # フロントエンドから送られてきた新しいデータ（data）で、設定を上書きする
    settings.show_duration = data.show_duration # 経過時間表示の ON/OFF
    settings.status_list = data.status_list     # ステータスの種類（カンマ区切りの文字列）
    
    db.commit() # データベースに上書きを確定（セーブ）
    return {"message": "Settings updated"} # 画面側に「保存成功したよ」と伝える