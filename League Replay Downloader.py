import os
import sys
import requests
import psutil
from PyQt5 import QtWidgets, QtCore, QtGui
import subprocess
from datetime import datetime
import time

def connect_to_lcu():
    """Connect to the League Client and get port and auth token."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        proc_name = proc.info['name']
        if proc_name in ['LeagueClientUx.exe', 'LeagueClientUx']:
            cmdline = proc.info['cmdline']
            port = None
            auth_token = None
            for arg in cmdline:
                if arg.startswith('--app-port='):
                    port = arg.split('=')[1]
                elif arg.startswith('--remoting-auth-token='):
                    auth_token = arg.split('=')[1]
            if port and auth_token:
                return {'port': port, 'auth_token': auth_token}
    return None

def list_available_replays(recently_downloaded):
    """Get a list of replay files sorted by date."""
    replay_dir = get_replay_directory()

    if not os.path.exists(replay_dir):
        return None, f"Replay directory not found: {replay_dir}"

    rofl_files = [f for f in os.listdir(replay_dir) if f.endswith('.rofl')]

    if not rofl_files:
        return None, "No replays found."

    replay_ids = []
    for file in rofl_files:
        filepath = os.path.join(replay_dir, file)
        filename = os.path.splitext(file)[0]
        parts = filename.split('-')
        if len(parts) == 2 and parts[1].isdigit():
            game_id = parts[1]
            is_recent = game_id in recently_downloaded
            mod_time = os.path.getmtime(filepath)
            replay_ids.append((game_id, is_recent, mod_time))

    if not replay_ids:
        return None, "No valid replays available."

    replay_ids.sort(key=lambda x: x[2], reverse=True)

    return replay_ids, None

def download_replay_api(game_id):
    """Download a replay using the API."""
    lcu_data = connect_to_lcu()

    if not lcu_data:
        return {'success': False, 'message': "LeagueClient not found. Ensure it's running and try again.", 'game_id': game_id}

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v1/rofls/{game_id}/download"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, auth=auth, json={}, headers=headers, verify=False)
    except requests.exceptions.ConnectionError:
        return {'success': False, 'message': "Connection failed. Make sure LeagueClient is running.", 'game_id': game_id}

    if response.status_code in [201, 204]:
        return {'success': True, 'message': "Download started!", 'game_id': game_id}
    elif response.status_code == 404:
        return {'success': False, 'message': f"Game ID {game_id} not found or replay unavailable.", 'game_id': game_id}
    else:
        return {'success': False, 'message': f"Error {response.status_code}: {response.text}", 'game_id': game_id}

def play_replay_api(game_id):
    """Play a replay using the API."""
    lcu_data = connect_to_lcu()

    if not lcu_data:
        return "LeagueClient not found. Ensure it's running and try again."

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v1/rofls/{game_id}/watch"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, auth=auth, json={}, headers=headers, verify=False)
    except requests.exceptions.ConnectionError:
        return "Connection failed. Make sure LeagueClient is running."

    if response.status_code in [200, 204]:
        return "Replay playback started!"
    elif response.status_code == 404:
        return f"Game ID {game_id} not found or replay unavailable."
    else:
        return f"Error {response.status_code}: {response.text}"

def get_replay_directory():
    """Return the default replay directory path."""
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, "Documents", "League of Legends", "Replays")

def launch_replay():
    """Open the latest replay file with the default application."""
    replay_dir = get_replay_directory()
    if not os.path.exists(replay_dir):
        return f"Replay directory not found: {replay_dir}"

    rofl_files = [f for f in os.listdir(replay_dir) if f.endswith('.rofl')]
    if not rofl_files:
        return "No replay files found."

    rofl_files.sort(key=lambda x: os.path.getmtime(os.path.join(replay_dir, x)), reverse=True)
    latest_replay = rofl_files[0]
    replay_path = os.path.join(replay_dir, latest_replay)

    try:
        if sys.platform.startswith("win"):
            os.startfile(replay_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", replay_path])
        else:
            subprocess.run(["xdg-open", replay_path])
        return f"Launching replay: {latest_replay}"
    except Exception as e:
        return f"Failed to launch replay: {e}"

def get_game_details(game_id):
    """Get game details for metadata creation."""
    lcu_data = connect_to_lcu()
    if not lcu_data:
        print("LeagueClient not found. Cannot get game details.")
        return None

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-match-history/v1/games/{game_id}"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.get(url, auth=auth, verify=False)
        if response.status_code == 200:
            game_info = response.json()
            game_version = game_info.get('gameVersion')
            game_type = game_info.get('gameType')
            queue_id = game_info.get('queueId')
            game_creation = game_info.get('gameCreation')
            game_duration = game_info.get('gameDuration')

            if game_creation and game_duration:
                game_end = game_creation + (game_duration * 1000)
            else:
                print(f"Missing gameCreation or gameDuration for game {game_id}.")
                return None

            if all([game_version, game_type, queue_id, game_end]):
                return {
                    "gameVersion": game_version,
                    "gameType": game_type,
                    "queueId": queue_id,
                    "gameEnd": game_end
                }
            else:
                print(f"Missing game details for game {game_id}.")
                return None
        else:
            print(f"Failed to get game details for game {game_id}: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("Failed to connect to LeagueClient for game details.")
        return None

def get_replay_metadata(game_id):
    """Fetch replay metadata from the API."""
    lcu_data = connect_to_lcu()

    if not lcu_data:
        print("LeagueClient not found. Cannot get metadata.")
        return None

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v1/metadata/{game_id}"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.get(url, auth=auth, verify=False)
        if response.status_code == 200:
            metadata = response.json()
            print(f"Metadata for game {game_id}: {metadata}")
            return metadata
        elif response.status_code == 404:
            print(f"Metadata for game {game_id} not found. Trying to create it.")
            game_details = get_game_details(game_id)
            if not game_details:
                print(f"Cannot create metadata without game details for game {game_id}.")
                return None
            create_url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v2/metadata/{game_id}/create"
            create_response = requests.post(create_url, auth=auth, json=game_details, verify=False)
            if create_response.status_code in [200, 201, 204]:
                print(f"Metadata creation requested for game {game_id}. Fetching again.")
                retry_response = requests.get(url, auth=auth, verify=False)
                if retry_response.status_code == 200:
                    metadata = retry_response.json()
                    print(f"Metadata for game {game_id}: {metadata}")
                    return metadata
                else:
                    print(f"Failed to fetch metadata after creation for game {game_id}: {retry_response.status_code} - {retry_response.text}")
                    return None
            else:
                print(f"Failed to create metadata for game {game_id}: {create_response.status_code} - {create_response.text}")
                return None
        else:
            print(f"Failed to get metadata for game {game_id}: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("Failed to connect to LeagueClient for metadata.")
        return None

def create_question_mark_icon(color="#FFFFFF", size=16):
    """Generate a simple question mark icon."""
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)

    pen = QtGui.QPen(QtGui.QColor(color))
    painter.setPen(pen)

    font = QtGui.QFont()
    font.setBold(True)
    font.setPointSize(size - 4)
    painter.setFont(font)

    rect = QtCore.QRect(0, 0, size, size)
    painter.drawText(rect, QtCore.Qt.AlignCenter, "?")

    painter.end()

    icon = QtGui.QIcon(pixmap)
    return icon

class CustomTableWidget(QtWidgets.QTableWidget):
    """Table to show replays."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Game ID", "Downloaded", "Date"])
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #2e3440;
                color: #d8dee9;
                border: none;
            }
            QHeaderView::section {
                background-color: #3b4252;
                color: #d8dee9;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #4c566a;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #4c566a;
            }
            QTableWidget::item:selected {
                background-color: #5e81ac;
                color: #d8dee9;
            }
        """)

    def populate_table(self, replay_list):
        """Fill the table with replay information."""
        self.setRowCount(len(replay_list))
        for row, (game_id, is_recent, mod_time) in enumerate(replay_list):
            game_id_item = QtWidgets.QTableWidgetItem(f"Game ID: {game_id}")
            game_id_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.setItem(row, 0, game_id_item)

            recent_item = QtWidgets.QTableWidgetItem("Yes" if is_recent else "No")
            recent_item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            color = QtGui.QColor("green") if is_recent else QtGui.QColor("white")
            recent_item.setForeground(QtGui.QBrush(color))
            self.setItem(row, 1, recent_item)

            formatted_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            date_item = QtWidgets.QTableWidgetItem(formatted_date)
            date_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.setItem(row, 2, date_item)

class ReplaysListDialog(QtWidgets.QDialog):
    """Dialog to display available replays."""
    def __init__(self, replay_list, game_id_entry, parent=None):
        super().__init__(parent)
        self.game_id_entry = game_id_entry  # Widget to set the selected game ID
        self.setWindowTitle("Available Replays")
        self.resize(720, 500)

        layout = QtWidgets.QVBoxLayout()
        self.table_widget = CustomTableWidget()

        self.table_widget.populate_table(replay_list)
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.table_widget.cellDoubleClicked.connect(self.cell_double_clicked)

        layout.addWidget(self.table_widget)
        self.setLayout(layout)

    def cell_double_clicked(self, row, column):
        """Set the selected Game ID and close the dialog."""
        game_id_item = self.table_widget.item(row, 0)
        if game_id_item:
            game_id = game_id_item.text().split(': ')[1]
            self.game_id_entry.setText(game_id)
            self.close()

class ResizeHandle(QtWidgets.QWidget):
    """Handle to resize the window."""
    def __init__(self, parent, handle_type):
        super().__init__(parent)
        self.handle_type = handle_type
        self.setFixedSize(10, 10)
        self.setStyleSheet("background-color: #4c566a;")
        self.setCursor(QtCore.Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        """Store initial mouse position and window size."""
        self.start_x = event.globalX()
        self.start_y = event.globalY()
        self.start_width = self.parent().width()
        self.start_height = self.parent().height()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Resize the window based on mouse movement."""
        delta_x = event.globalX() - self.start_x
        delta_y = event.globalY() - self.start_y
        parent = self.parent()
        if self.handle_type == 'bottom_right':
            new_width = self.start_width + delta_x
            new_height = self.start_height + delta_y
            parent.resize(new_width, new_height)
        elif self.handle_type == 'bottom_left':
            new_width = self.start_width - delta_x
            new_height = self.start_height + delta_y
            parent.setGeometry(parent.x() + delta_x, parent.y(), new_width, new_height)
        elif self.handle_type == 'top_right':
            new_width = self.start_width + delta_x
            new_height = self.start_height - delta_y
            parent.setGeometry(parent.x(), parent.y() + delta_y, new_width, new_height)
        elif self.handle_type == 'top_left':
            new_width = self.start_width - delta_x
            new_height = self.start_height - delta_y
            parent.setGeometry(parent.x() + delta_x, parent.y() + delta_y, new_width, new_height)
        super().mouseMoveEvent(event)

class HelpDialog(QtWidgets.QDialog):
    """Dialog with helpful links."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Useful Links")
        self.resize(600, 200)

        layout = QtWidgets.QVBoxLayout()

        links = [
            ('Link to GitHub', 'https://github.com/Rayan0000000/League-Replay-Downloader'),
            ('Showcase of the Downloader', 'https://example.com/showcase'),
            ('Guide to Download Expired Replays', 'https://youtu.be/TQf838yEi5I?si=EYJMZIKBszwOZ_to')
        ]

        for text, url in links:
            label = QtWidgets.QLabel(f'<a href="{url}" style="color: white; text-decoration: none;">{text}</a>')
            label.setOpenExternalLinks(True)
            label.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(label)

        self.setLayout(layout)

class ReplayDownloaderApp(QtWidgets.QWidget):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.is_moving = False
        self.recently_downloaded = []

    def init_ui(self):
        self.setWindowTitle("League Replay Downloader")
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setFixedSize(400, 400)

        # Title bar
        self.title_bar = QtWidgets.QWidget(self)
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("background-color: #3b4252;")
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 10, 0)

        title_label = QtWidgets.QLabel("League Replay Downloader", self)
        title_label.setStyleSheet("color: #d8dee9; font-weight: bold; font-size: 12px;")

        # Close button
        close_button = QtWidgets.QPushButton()
        close_icon = self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton)
        close_button.setIcon(close_icon)
        close_button.setIconSize(QtCore.QSize(16, 16))
        close_button.setFixedSize(24, 24)
        close_button.setStyleSheet("background-color: transparent;")
        close_button.clicked.connect(self.close)

        # Help button
        help_icon = create_question_mark_icon(color="#FFFFFF")
        help_button = QtWidgets.QPushButton()
        help_button.setIcon(help_icon)
        help_button.setIconSize(QtCore.QSize(16, 16))
        help_button.setFixedSize(24, 24)
        help_button.setStyleSheet("background-color: transparent;")
        help_button.clicked.connect(self.show_help_dialog)

        title_layout.addWidget(title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(help_button)
        title_layout.addWidget(close_button)
        self.title_bar.setLayout(title_layout)

        # Main content
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        main_layout.setContentsMargins(0, 0, 0, 0)
        content_layout = QtWidgets.QVBoxLayout()

        self.game_id_label = QtWidgets.QLabel("Enter Game ID:")
        self.game_id_label.setStyleSheet("font-size: 12px;")
        game_id_entry = QtWidgets.QLineEdit()
        game_id_entry.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #4c566a;
                border-radius: 4px;
                background-color: #3b4252;
                font-size: 12px;
            }
        """)
        self.game_id_entry = game_id_entry
        content_layout.addWidget(self.game_id_label)
        content_layout.addWidget(game_id_entry)

        self.list_replays_button = QtWidgets.QPushButton("List Available Replays")
        self.list_replays_button.clicked.connect(self.list_replays)
        content_layout.addWidget(self.list_replays_button)

        self.download_button = QtWidgets.QPushButton("Download Replay")
        self.download_button.clicked.connect(self.download_replay)
        content_layout.addWidget(self.download_button)

        self.start_replay_button = QtWidgets.QPushButton("Start Replay")
        self.start_replay_button.clicked.connect(self.start_replay_combined)
        self.start_replay_button.setEnabled(True)
        content_layout.addWidget(self.start_replay_button)

        self.response_label = QtWidgets.QLabel("")
        self.response_label.setStyleSheet("font-size: 12px;")
        content_layout.addWidget(self.response_label)

        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2e3440;
                color: #d8dee9;
                font-family: 'Inter', Arial, sans-serif;
            }
            QPushButton {
                padding: 8px;
                border: 1px solid #4c566a;
                border-radius: 4px;
                background-color: #4c566a;
                color: #d8dee9;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5e81ac;
            }
            QLabel {
                padding: 4px;
                font-size: 12px;
            }
        """)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # Resize handles
        self.resize_handle_br = ResizeHandle(self, 'bottom_right')
        self.resize_handle_br.move(self.width() - 10, self.height() - 10)
        self.resize_handle_bl = ResizeHandle(self, 'bottom_left')
        self.resize_handle_bl.move(0, self.height() - 10)
        self.resize_handle_tr = ResizeHandle(self, 'top_right')
        self.resize_handle_tr.move(self.width() - 10, 0)
        self.resize_handle_tl = ResizeHandle(self, 'top_left')
        self.resize_handle_tl.move(0, 0)

    def mousePressEvent(self, event):
        """Start moving the window if the title bar is clicked."""
        if event.button() == QtCore.Qt.LeftButton and self.title_bar.underMouse():
            self.start_x = event.globalX()
            self.start_y = event.globalY()
            self.is_moving = True
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Move the window based on mouse movement."""
        if self.is_moving:
            delta_x = event.globalX() - self.start_x
            delta_y = event.globalY() - self.start_y
            self.move(self.x() + delta_x, self.y() + delta_y)
            self.start_x = event.globalX()
            self.start_y = event.globalY()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Stop moving the window when the mouse is released."""
        if event.button() == QtCore.Qt.LeftButton:
            self.is_moving = False
            self.setCursor(QtCore.Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def list_replays(self):
        """Display available replays in a dialog."""
        replay_list, error_message = list_available_replays(self.recently_downloaded)
        if error_message:
            self.response_label.setText(error_message)
            return
        if replay_list:
            dialog = ReplaysListDialog(replay_list, self.game_id_entry, self)
            dialog.exec_()
        else:
            self.response_label.setText("No replays available.")

    def download_replay(self):
        """Start downloading the entered replay."""
        game_id = self.game_id_entry.text().strip()
        if not game_id:
            self.response_label.setText("Please enter a Game ID.")
            return
        if not game_id.isdigit():
            self.response_label.setText("Invalid Game ID. Enter a numeric ID.")
            return

        self.download_button.setEnabled(False)
        self.response_label.setText("Download started...")

        self.thread = QtCore.QThread()
        self.worker = ReplayDownloaderWorker(game_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_download_finished(self, result):
        """Update UI after download completes."""
        if result['success']:
            self.response_label.setText(result['message'])
            self.recently_downloaded.append(result['game_id'])
        else:
            self.response_label.setText(result['message'])
        self.download_button.setEnabled(True)

    def start_replay_combined(self):
        """Start replay playback via API."""
        game_id = self.game_id_entry.text().strip()
        if not game_id:
            self.response_label.setText("Please enter a Game ID.")
            return
        if not game_id.isdigit():
            self.response_label.setText("Invalid Game ID. Enter a numeric ID.")
            return

        self.start_replay_button.setEnabled(False)
        self.response_label.setText("Starting replay...")

        self.thread = QtCore.QThread()
        self.worker = ReplayLauncherWorker(game_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_play_combined_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_play_combined_finished(self, result):
        """Update UI after attempting to start replay."""
        self.response_label.setText(result)
        self.start_replay_button.setEnabled(True)

    def show_help_dialog(self):
        """Show the help dialog with useful links."""
        dialog = HelpDialog(self)
        dialog.exec_()

class ReplayDownloaderWorker(QtCore.QObject):
    """Handles replay downloading in a separate thread."""
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, game_id):
        super().__init__()
        self.game_id = game_id

    def run(self):
        metadata = get_replay_metadata(self.game_id)
        if metadata is None:
            result = {'success': False, 'message': "Failed to get replay metadata.", 'game_id': self.game_id}
            self.finished.emit(result)
            return

        state = metadata.get('state', '').lower()
        print(f"Initial replay state for game {self.game_id}: {state}")

        if state == 'download':
            download_result = download_replay_api(self.game_id)
            print(f"Download response for Game ID {self.game_id}: {download_result['message']}")
            if not download_result['success']:
                self.finished.emit(download_result)
                return

            max_attempts = 8
            attempts = 0
            while attempts < max_attempts:
                time.sleep(1)
                metadata = get_replay_metadata(self.game_id)
                if metadata:
                    current_state = metadata.get('state', '').lower()
                    print(f"Replay state for game {self.game_id}: {current_state}")
                    if current_state == 'watch':
                        success_result = {'success': True, 'message': f"Replay {self.game_id} downloaded successfully.", 'game_id': self.game_id}
                        self.finished.emit(success_result)
                        return
                attempts += 1
                print(f"Attempt {attempts}/{max_attempts} to check replay status.")

            timeout_result = {'success': False, 'message': f"Download timed out for Replay {self.game_id}.", 'game_id': self.game_id}
            self.finished.emit(timeout_result)
        elif state == 'incompatible':
            message = "Cannot download replay from a different patch."
            result = {'success': False, 'message': message, 'game_id': self.game_id}
            self.finished.emit(result)
        elif state == 'watch':
            message = "Replay already downloaded."
            result = {'success': False, 'message': message, 'game_id': self.game_id}
            self.finished.emit(result)
        else:
            message = f"Unknown replay state: {state}"
            result = {'success': False, 'message': message, 'game_id': self.game_id}
            self.finished.emit(result)

class ReplayLauncherWorker(QtCore.QObject):
    """Handles replay launching in a separate thread."""
    finished = QtCore.pyqtSignal(str)

    def __init__(self, game_id):
        super().__init__()
        self.game_id = game_id

    def run(self):
        metadata = get_replay_metadata(self.game_id)
        if metadata is None:
            self.finished.emit("Failed to get replay metadata.")
            return

        state = metadata.get('state', '').lower()
        print(f"Replay state for game {self.game_id}: {state}")

        if state == 'watch':
            result = play_replay_api(self.game_id)
            self.finished.emit(result)
        elif state == 'incompatible':
            message = "Cannot play replay from a different patch."
            self.finished.emit(message)
        elif state == 'download':
            message = "Download the replay first."
            self.finished.emit(message)
        else:
            message = f"Unknown replay state: {state}"
            self.finished.emit(message)

def main():
    """Start the application."""
    app = QtWidgets.QApplication(sys.argv)
    window = ReplayDownloaderApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
