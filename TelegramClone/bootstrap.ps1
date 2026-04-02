# bootstrap.ps1 – запускает сервер, генерирует ключ, регистрирует user1, стартует клиент

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$project = "D:\TelegramClone"
Set-Location $project

Write-Host "`n[1/5] Установка зависимостей..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

Write-Host "[2/5] Запуск сервера в отдельном окне..."
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$project'; python app.py"
Start-Sleep -Seconds 4

Write-Host "[3/5] Генерация invite_key..."
$raw = python -c @"
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:5000/generate_invite',
    data=json.dumps({'admin_key':'admin-secret'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
print(json.loads(resp.read())['invite_key'])
"@
$inviteKey = $raw.Trim()
Write-Host "   invite_key = $inviteKey"

Write-Host "[4/5] Регистрация user1 / password: 123456..."
python -c @"
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:5000/register',
    data=json.dumps({'username':'user1','password':'123456','invite_key':'$inviteKey'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
print(json.loads(resp.read()))
"@

Write-Host "[5/5] Запуск Kivy клиента..."
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location '$project'; python kivy_client.py"

Write-Host "`n=== Готово ==="
Write-Host "  username  : user1"
Write-Host "  password  : 123456"
Write-Host "  invite_key: $inviteKey (уже использован)"
Write-Host "  сервер    : http://127.0.0.1:5000"
