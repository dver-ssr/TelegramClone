[app]
title = TelegramClone
package.name = telegramclone
package.domain = org.example
source.dir = .
source.main = kivy_client.py
version = 0.1
requirements = python3,kivy==2.3.0,python-socketio,requests
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
