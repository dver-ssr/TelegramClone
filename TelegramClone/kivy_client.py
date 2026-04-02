import requests
import socketio
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock

SERVER_URL = 'http://127.0.0.1:5000'

sio = socketio.Client()

KV = '''
<Screen>:
    orientation: 'vertical'
    padding: '12dp'
    spacing: '8dp'
    canvas.before:
        Color:
            rgba: 0.13, 0.16, 0.21, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # ── Шапка ──────────────────────────────────────────────────
    Label:
        text: 'TelegramClone'
        size_hint_y: None
        height: '36dp'
        font_size: '20sp'
        bold: True
        color: 0.29, 0.56, 0.89, 1

    Label:
        id: status_label
        text: 'Статус: ' + root.status
        size_hint_y: None
        height: '24dp'
        font_size: '13sp'
        color: 0.7, 0.7, 0.7, 1

    # ── Авторизация ────────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: '6dp'
        TextInput:
            id: tf_username
            hint_text: 'username'
            on_text: root.username = self.text
            background_color: 0.19, 0.22, 0.29, 1
            foreground_color: 1, 1, 1, 1
        TextInput:
            id: tf_password
            hint_text: 'password'
            password: True
            on_text: root.password = self.text
            background_color: 0.19, 0.22, 0.29, 1
            foreground_color: 1, 1, 1, 1

    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: '6dp'
        TextInput:
            id: tf_invite
            hint_text: 'invite_key (для регистрации)'
            on_text: root.invite_key = self.text
            background_color: 0.19, 0.22, 0.29, 1
            foreground_color: 1, 1, 1, 1
        Button:
            text: 'Регистрация'
            size_hint_x: None
            width: '120dp'
            background_color: 0.18, 0.48, 0.77, 1
            on_release: root.do_register()
        Button:
            text: 'Вход'
            size_hint_x: None
            width: '80dp'
            background_color: 0.18, 0.65, 0.45, 1
            on_release: root.do_login()

    # ── Комната и подключение ──────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: '6dp'
        TextInput:
            id: tf_room
            hint_text: 'Комната (напр. general)'
            text: root.room
            on_text: root.room = self.text
            background_color: 0.19, 0.22, 0.29, 1
            foreground_color: 1, 1, 1, 1
        Button:
            text: 'Подключиться'
            size_hint_x: None
            width: '140dp'
            background_color: 0.18, 0.48, 0.77, 1
            on_release: root.do_connect()
        Button:
            text: 'Выйти'
            size_hint_x: None
            width: '80dp'
            background_color: 0.6, 0.2, 0.2, 1
            on_release: root.do_disconnect()

    # ── Сообщения ──────────────────────────────────────────────
    ScrollView:
        id: scroll
        GridLayout:
            id: messages
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            spacing: '4dp'

    # ── Ввод сообщения ─────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: '44dp'
        spacing: '6dp'
        TextInput:
            id: tf_msg
            hint_text: 'Написать сообщение...'
            background_color: 0.19, 0.22, 0.29, 1
            foreground_color: 1, 1, 1, 1
        Button:
            text: 'Отправить'
            size_hint_x: None
            width: '110dp'
            background_color: 0.18, 0.48, 0.77, 1
            on_release: root.send_message()
'''

class Screen(BoxLayout):
    username = StringProperty('')
    password = StringProperty('')
    invite_key = StringProperty('')
    room = StringProperty('general')
    status = StringProperty('offline')
    authenticated = BooleanProperty(False)

    def _add_msg(self, user, text, color=(1, 1, 1, 1)):
        lbl = Label(
            text=f'[b]{user}:[/b] {text}',
            markup=True,
            size_hint_y=None,
            height='34dp',
            text_size=(self.width - 24, None),
            halign='left',
            valign='middle',
            color=color,
        )
        lbl.bind(texture_size=lambda w, ts: setattr(w, 'height', max(34, ts[1] + 8)))
        self.ids.messages.add_widget(lbl)
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll, 'scroll_y', 0), 0.05)

    def add_msg(self, data):
        self._add_msg(data.get('user', '?'), data.get('msg', ''))

    def add_system(self, text):
        self._add_msg('system', text, color=(0.6, 0.6, 0.6, 1))

    def load_history(self, history):
        self.ids.messages.clear_widgets()
        for item in history:
            self.add_msg(item)

    def do_register(self):
        if not self.username or not self.password or not self.invite_key:
            self.status = 'Заполни все поля + invite_key'
            return
        try:
            r = requests.post(f'{SERVER_URL}/register', json={
                'username': self.username,
                'password': self.password,
                'invite_key': self.invite_key
            }, timeout=5)
            data = r.json()
            self.status = 'Зарегистрирован! Войди.' if r.status_code == 200 else data.get('error', 'Ошибка')
        except Exception as e:
            self.status = f'Ошибка: {e}'

    def do_login(self):
        if not self.username or not self.password:
            self.status = 'Нужны username и password'
            return
        try:
            r = requests.post(f'{SERVER_URL}/login', json={
                'username': self.username,
                'password': self.password
            }, timeout=5)
            data = r.json()
            if r.status_code == 200:
                self.authenticated = True
                self.status = f'Вход выполнен: {self.username}'
            else:
                self.status = data.get('error', 'Ошибка входа')
        except Exception as e:
            self.status = f'Ошибка: {e}'

    def do_connect(self):
        if not self.authenticated:
            self.status = 'Сначала войди!'
            return
        try:
            if sio.connected:
                sio.disconnect()
            sio.connect(SERVER_URL)
            sio.emit('join', {'username': self.username, 'room': self.room})
            self.status = f'online [{self.room}]'
        except Exception as e:
            self.status = f'Ошибка подключения: {e}'

    def send_message(self):
        text = self.ids.tf_msg.text.strip()
        if not text or not sio.connected:
            return
        sio.emit('text', {'room': self.room, 'msg': text})
        self.ids.tf_msg.text = ''

    def do_disconnect(self):
        if sio.connected:
            sio.emit('leave', {'room': self.room})
            sio.disconnect()
        self.status = 'offline'


# ── Socket.IO события ─────────────────────────────────────────────────────────

@sio.on('message')
def on_message(data):
    app = App.get_running_app()
    if app:
        Clock.schedule_once(lambda dt: app.root.add_msg(data), 0)

@sio.on('status')
def on_status(data):
    app = App.get_running_app()
    if app:
        Clock.schedule_once(lambda dt: app.root.add_system(data.get('msg', '')), 0)

@sio.on('history')
def on_history(data):
    app = App.get_running_app()
    if app:
        Clock.schedule_once(lambda dt: app.root.load_history(data), 0)

@sio.on('error')
def on_error(data):
    app = App.get_running_app()
    if app:
        Clock.schedule_once(lambda dt: setattr(app.root, 'status', data.get('msg', 'Ошибка')), 0)


# ── App ───────────────────────────────────────────────────────────────────────

class MessengerApp(App):
    title = 'TelegramClone'

    def build(self):
        Builder.load_string(KV)
        return Screen()

    def on_stop(self):
        if sio.connected:
            sio.disconnect()


if __name__ == '__main__':
    MessengerApp().run()
