RENDER:
1. Upload all files to GitHub.
2. Render -> New -> Blueprint -> select repo.
3. render.yaml creates Web + PostgreSQL.
4. Set ADMIN_USER and ADMIN_PASS in Web Environment.
5. Deploy.
SHOP: https://TEN-SERVICE.onrender.com/
ADMIN: https://TEN-SERVICE.onrender.com/admin
Files: app.py, requirements.txt, render.yaml, Procfile, static/shop.html, static/admin.html.
Data and uploaded images are stored in PostgreSQL, so everyone sees the same products.
