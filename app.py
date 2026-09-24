import os, uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory, session, abort, Response

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret')
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024
DATABASE_URL = os.environ.get('DATABASE_URL')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

def conn():
    if not DATABASE_URL: raise RuntimeError('DATABASE_URL chưa được cấu hình')
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS accounts (id UUID PRIMARY KEY,name TEXT NOT NULL,code TEXT NOT NULL,price BIGINT NOT NULL DEFAULT 0,description TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'available',created_at TIMESTAMPTZ DEFAULT NOW());''')
            cur.execute('''CREATE TABLE IF NOT EXISTS account_images (id BIGSERIAL PRIMARY KEY,account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,image_data BYTEA NOT NULL,mime TEXT NOT NULL,position INTEGER NOT NULL DEFAULT 0);''')

def admin_ok(): return session.get('admin') is True

@app.get('/')
def shop(): return send_from_directory(app.static_folder,'shop.html')
@app.get('/admin')
def admin(): return send_from_directory(app.static_folder,'admin.html')

@app.post('/api/login')
def login():
    d=request.get_json(silent=True) or {}
    if d.get('username')==ADMIN_USER and d.get('password')==ADMIN_PASS:
        session['admin']=True; return jsonify(ok=True)
    return jsonify(ok=False,error='Sai tài khoản hoặc mật khẩu'),401
@app.post('/api/logout')
def logout(): session.clear(); return jsonify(ok=True)
@app.get('/api/me')
def me(): return jsonify(admin=admin_ok())

@app.get('/api/accounts')
def accounts():
    with conn() as c:
        with c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''SELECT a.id::text,a.name,a.code,a.price,a.description,a.status,COALESCE(json_agg(json_build_object('id',i.id,'url','/api/images/'||i.id) ORDER BY i.position) FILTER (WHERE i.id IS NOT NULL),'[]') images FROM accounts a LEFT JOIN account_images i ON i.account_id=a.id GROUP BY a.id ORDER BY a.created_at DESC''')
            return jsonify(cur.fetchall())

@app.get('/api/images/<int:image_id>')
def image(image_id):
    with conn() as c:
        with c.cursor() as cur:
            cur.execute('SELECT image_data,mime FROM account_images WHERE id=%s',(image_id,)); row=cur.fetchone()
            if not row: abort(404)
            return Response(bytes(row[0]),mimetype=row[1],headers={'Cache-Control':'public,max-age=31536000'})

@app.post('/api/accounts')
def add_account():
    name=request.form.get('name','').strip(); code=request.form.get('code','').strip(); desc=request.form.get('description','').strip(); status=request.form.get('status','available')
    try: price=int(request.form.get('price','0'))
    except ValueError: price=0
    if not name or not code: return jsonify(error='Thiếu tên acc hoặc mã acc'),400
    if status not in ('available','sold'): status='available'
    files=[f for f in request.files.getlist('images') if f and f.filename][:10]
    aid=uuid.uuid4()
    with conn() as c:
        with c.cursor() as cur:
            cur.execute('INSERT INTO accounts(id,name,code,price,description,status) VALUES(%s,%s,%s,%s,%s,%s)',(aid,name,code,price,desc,status))
            for pos,f in enumerate(files):
                data=f.read()
                if len(data)>8*1024*1024 or not (f.mimetype or '').startswith('image/'): continue
                cur.execute('INSERT INTO account_images(account_id,image_data,mime,position) VALUES(%s,%s,%s,%s)',(aid,psycopg2.Binary(data),f.mimetype,pos))
    return jsonify(ok=True,id=str(aid))

@app.post('/api/accounts/<account_id>/status')
def status(account_id):
    s=(request.get_json(silent=True) or {}).get('status')
    if s not in ('available','sold'): return jsonify(error='Trạng thái không hợp lệ'),400
    with conn() as c:
        with c.cursor() as cur: cur.execute('UPDATE accounts SET status=%s WHERE id=%s',(s,account_id))
    return jsonify(ok=True)

@app.delete('/api/accounts/<account_id>')
def delete(account_id):
    with conn() as c:
        with c.cursor() as cur: cur.execute('DELETE FROM accounts WHERE id=%s',(account_id,))
    return jsonify(ok=True)

try: init_db()
except Exception as e: print('Database chưa sẵn sàng:',e)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
