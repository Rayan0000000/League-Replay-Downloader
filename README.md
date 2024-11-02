# 🎮 League Replay Downloader

> A simple tool to download and play League of Legends replays by entering the Game ID.

![League Replay Downloader Screenshot](https://i.imgur.com/d4fV29G.png)

## 🚀 Overview

The **League Replay Downloader** allows you to easily download and play League of Legends replays by entering the Game ID. Simply ensure that the replay version matches the current patch on your League Client, and you’re ready to go!

---

## 📦 Features

- **Download Replays**: Quickly download replays from the League Client by entering the Game ID.
- **Play Replays**: Start replay playback directly in the client or open the replay file on your system.
- **Organized Replay List**: View available replays in your League of Legends replay folder.

## ⚙️ Requirements

### For Windows Users

- **Option 1**: Download the `.exe` file (no Python installation required).
- **Option 2**: Run the Python script (requires Python 3.7 or later and additional dependencies listed below).

### For macOS

- **Python 3.7 or later**: Required to run the Python script.
- **Dependencies**:
  - [PyQt5](https://pypi.org/project/PyQt5/) - For the application’s graphical interface.
  - [Requests](https://pypi.org/project/requests/) - To handle HTTP requests for League Client API.
  - [Psutil](https://pypi.org/project/psutil/) - To locate and connect to the League Client.

To install dependencies, you can run:

```bash
pip install -r requirements.txt
