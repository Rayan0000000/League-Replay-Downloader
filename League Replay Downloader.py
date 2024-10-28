import os
import sys
import requests
import psutil
from PyQt5 import QtWidgets, QtCore, QtGui
import subprocess

def connect_to_lcu():
    """
    Connects to the League Client by locating the 'LeagueClientUx' process.
    Retrieves the port and authentication token needed for API communication.
    """
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
    """
    Scans the replay directory for .rofl files and extracts their Game IDs.
    """
    replay_dir = get_replay_directory()

    if not os.path.exists(replay_dir):
        return None, f"Replay directory does not exist: {replay_dir}"

    rofl_files = [f for f in os.listdir(replay_dir) if f.endswith('.rofl')]

    if not rofl_files:
        return None, "No replays available."

    replay_ids = []
    for file in rofl_files:
        filename = os.path.splitext(file)[0]
        parts = filename.split('-')
        if len(parts) == 2 and parts[1].isdigit():
            game_id = parts[1]
            is_recent = game_id in recently_downloaded
            replay_ids.append((game_id, is_recent))

    if not replay_ids:
        return None, "No valid replays available."

    return replay_ids, None

def download_replay(game_id):
    """
    Initiates the download of a replay from the League Client.
    """
    lcu_data = connect_to_lcu()

    if not lcu_data:
        return {'success': False, 'message': "LeagueClient not found. Make sure the client is running and try again.", 'game_id': game_id}

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v1/rofls/{game_id}/download"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, auth=auth, json={}, headers=headers, verify=False)
    except requests.exceptions.ConnectionError:
        return {'success': False, 'message': "Failed to connect. Make sure the LeagueClient is running.", 'game_id': game_id}

    if response.status_code in [201, 204]:
        return {'success': True, 'message': "Replay download started successfully!", 'game_id': game_id}
    elif response.status_code == 404:
        return {'success': False, 'message': f"Game with ID {game_id} not found or replay is unavailable.", 'game_id': game_id}
    else:
        response_text = response.text
        return {'success': False, 'message': f"Error: {response.status_code} - {response_text}", 'game_id': game_id}

def play_replay_api(game_id):
    """
    Starts replay playback using the League Client API.
    """
    lcu_data = connect_to_lcu()

    if not lcu_data:
        return "LeagueClient not found. Make sure the client is running and try again."

    url = f"https://127.0.0.1:{lcu_data['port']}/lol-replays/v1/rofls/{game_id}/watch"
    auth = requests.auth.HTTPBasicAuth('riot', lcu_data['auth_token'])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, auth=auth, json={}, headers=headers, verify=False)
    except requests.exceptions.ConnectionError:
        return "Failed to connect. Make sure the LeagueClient is running."

    if response.status_code in [200, 204]:
        return "Replay playback started successfully!"
    elif response.status_code == 404:
        return f"Game with ID {game_id} not found or replay is unavailable."
    else:
        response_text = response.text
        return f"Error: {response.status_code} - {response_text}"

def get_replay_directory():
    """
    Determines the default replay directory based on the operating system.
    """
    home_dir = os.path.expanduser("~")
    replay_dir = os.path.join(home_dir, "Documents", "League of Legends", "Replays")
    return replay_dir

def launch_replay():
    """
    Opens the most recent replay file using the system's default application.
    """
    replay_dir = get_replay_directory()
    if not os.path.exists(replay_dir):
        return f"Replay directory does not exist: {replay_dir}"

    rofl_files = [f for f in os.listdir(replay_dir) if f.endswith('.rofl')]
    if not rofl_files:
        return "No replay files found in the replay directory."

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

def create_question_mark_icon(color="#FFFFFF", size=16):
    """
    Creates a question mark icon with the specified color and size.
    """
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

class CustomListWidget(QtWidgets.QListWidget):
    """
    Custom list widget that scrolls one item per wheel notch.
    """
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        steps = int(delta / 120)
        if steps > 0:
            for _ in range(steps):
                self.verticalScrollBar().triggerAction(QtWidgets.QAbstractSlider.SliderSingleStepSub)
        elif steps < 0:
            for _ in range(-steps):
                self.verticalScrollBar().triggerAction(QtWidgets.QAbstractSlider.SliderSingleStepAdd)
        event.accept()

class ReplaysListDialog(QtWidgets.QDialog):
    """
    Dialog that displays available replays.
    """
    def __init__(self, replay_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Available Replays")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout()
        self.list_widget = CustomListWidget()

        self.list_widget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.list_widget.verticalScrollBar().setInvertedAppearance(False)
        self.list_widget.verticalScrollBar().setInvertedControls(False)

        for game_id, is_recent in replay_list:
            item_text = f"Game ID: {game_id}"
            if is_recent:
                item_text += " (Recently Downloaded)"
            self.list_widget.addItem(item_text)

        if self.list_widget.count() > 0:
            item_height = self.list_widget.sizeHintForRow(0)
            self.list_widget.verticalScrollBar().setSingleStep(item_height)

        self.list_widget.itemDoubleClicked.connect(self.item_double_clicked)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def item_double_clicked(self, item):
        game_id = item.text().split(': ')[1].split()[0].strip()
        self.parent().game_id_input.setText(game_id)
        self.close()

class ResizeHandle(QtWidgets.QWidget):
    """
    Widget to handle window resizing.
    """
    def __init__(self, parent, handle_type):
        super().__init__(parent)
        self.handle_type = handle_type
        self.setFixedSize(10, 10)
        self.setStyleSheet("background-color: #4c566a;")
        self.setCursor(QtCore.Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        self.start_x = event.globalX()
        self.start_y = event.globalY()
        self.start_width = self.parent().width()
        self.start_height = self.parent().height()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        delta_x = event.globalX() - self.start_x
        delta_y = event.globalY() - self.start_y
        if self.handle_type == 'bottom_right':
            new_width = self.start_width + delta_x
            new_height = self.start_height + delta_y
            self.parent().resize(new_width, new_height)
        elif self.handle_type == 'bottom_left':
            new_width = self.start_width - delta_x
            new_height = self.start_height + delta_y
            self.parent().setGeometry(self.parent().x() + delta_x, self.parent().y(), new_width, new_height)
        elif self.handle_type == 'top_right':
            new_width = self.start_width + delta_x
            new_height = self.start_height - delta_y
            self.parent().setGeometry(self.parent().x(), self.parent().y() + delta_y, new_width, new_height)
        elif self.handle_type == 'top_left':
            new_width = self.start_width - delta_x
            new_height = self.start_height - delta_y
            self.parent().setGeometry(self.parent().x() + delta_x, self.parent().y() + delta_y, new_width, new_height)
        super().mouseMoveEvent(event)

class HelpDialog(QtWidgets.QDialog):
    """
    Dialog that provides useful links.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Useful Links")
        self.resize(400, 200)

        layout = QtWidgets.QVBoxLayout()

        label1 = QtWidgets.QLabel('<a href="https://github.com/Rayan0000000/League-Replay-Downloader" style="color: white; text-decoration: none;">Link to GitHub</a>')
        label1.setOpenExternalLinks(True)

        label2 = QtWidgets.QLabel('<a href="coming soon" style="color: white; text-decoration: none;">Link to a showcase of using the League Replay Downloader</a>')
        label2.setOpenExternalLinks(True)

        label3 = QtWidgets.QLabel('<a href="https://youtu.be/TQf838yEi5I?si=EYJMZIKBszwOZ_to" style="color: white; text-decoration: none;">Link to a Guide on how to download expired Replays</a>')
        label3.setOpenExternalLinks(True)

        layout.addWidget(label1)
        layout.addWidget(label2)
        layout.addWidget(label3)

        self.setLayout(layout)

class ReplayDownloaderApp(QtWidgets.QWidget):
    """
    Main application window for the Replay Downloader.
    """
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
        title_label.setStyleSheet("color: #d8dee9; font-weight: bold;")

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
        self.game_id_input = QtWidgets.QLineEdit()
        content_layout.addWidget(self.game_id_label)
        content_layout.addWidget(self.game_id_input)

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
        content_layout.addWidget(self.response_label)

        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2e3440;
                color: #d8dee9;
                font-family: 'Inter', Arial, sans-serif;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #4c566a;
                border-radius: 4px;
                background-color: #3b4252;
            }
            QPushButton {
                padding: 8px;
                border: 1px solid #4c566a;
                border-radius: 4px;
                background-color: #4c566a;
                color: #d8dee9;
            }
            QPushButton:hover {
                background-color: #5e81ac;
            }
            QLabel {
                padding: 4px;
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
        if event.button() == QtCore.Qt.LeftButton and self.title_bar.underMouse():
            self.start_x = event.globalX()
            self.start_y = event.globalY()
            self.is_moving = True
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_moving:
            delta_x = event.globalX() - self.start_x
            delta_y = event.globalY() - self.start_y
            self.move(self.x() + delta_x, self.y() + delta_y)
            self.start_x = event.globalX()
            self.start_y = event.globalY()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_moving = False
            self.setCursor(QtCore.Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def list_replays(self):
        """
        Displays a dialog with available replays.
        """
        replay_list, error_message = list_available_replays(self.recently_downloaded)
        if error_message:
            self.response_label.setText(error_message)
            return
        if replay_list:
            dialog = ReplaysListDialog(replay_list, self)
            dialog.exec_()
        else:
            self.response_label.setText("No replays available.")

    def download_replay(self):
        """
        Starts the replay download process.
        """
        game_id = self.game_id_input.text().strip()
        if not game_id:
            self.response_label.setText("Please enter a Game ID.")
            return
        if not game_id.isdigit():
            self.response_label.setText("Invalid Game ID. Please enter a numeric ID.")
            return

        self.download_button.setEnabled(False)
        self.start_replay_button.setEnabled(True)
        self.response_label.setText("Downloading replay...")

        self.thread = QtCore.QThread()
        self.worker = ReplayDownloaderWorker(game_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def start_replay_combined(self):
        """
        Attempts to start replay via API, falls back to file launch if needed.
        """
        game_id = self.game_id_input.text().strip()
        if not game_id:
            self.response_label.setText("Please enter a Game ID.")
            return
        if not game_id.isdigit():
            self.response_label.setText("Invalid Game ID. Please enter a numeric ID.")
            return

        self.start_replay_button.setEnabled(False)
        self.response_label.setText("Launching replay...")

        self.thread = QtCore.QThread()
        self.worker = ReplayLauncherWorker(game_id, method='combined')
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_play_combined_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_download_finished(self, result):
        """
        Handles the result of the download process.
        """
        self.response_label.setText(result['message'])
        if result['success']:
            self.recently_downloaded.append(result['game_id'])
        self.download_button.setEnabled(True)

    def on_play_combined_finished(self, result):
        """
        Handles the result of the replay launch process.
        """
        self.response_label.setText(result)
        self.start_replay_button.setEnabled(True)

    def show_help_dialog(self):
        """
        Opens the Help dialog.
        """
        dialog = HelpDialog(self)
        dialog.exec_()

class ReplayDownloaderWorker(QtCore.QObject):
    """
    Worker thread for downloading replays.
    """
    finished = QtCore.pyqtSignal(dict)

    def __init__(self, game_id):
        super().__init__()
        self.game_id = game_id

    def run(self):
        result = download_replay(self.game_id)
        self.finished.emit(result)

class ReplayLauncherWorker(QtCore.QObject):
    """
    Worker thread for launching replays.
    """
    finished = QtCore.pyqtSignal(str)

    def __init__(self, game_id, method='combined'):
        super().__init__()
        self.game_id = game_id
        self.method = method

    def run(self):
        if self.method == 'api':
            result = play_replay_api(self.game_id)
        elif self.method == 'file':
            result = launch_replay()
        elif self.method == 'combined':
            result = play_replay_api(self.game_id)
            if not result.lower().startswith("replay playback started successfully"):
                fallback_result = launch_replay()
                result += " | " + fallback_result
        else:
            result = "Unknown method."
        self.finished.emit(result)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ReplayDownloaderApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
