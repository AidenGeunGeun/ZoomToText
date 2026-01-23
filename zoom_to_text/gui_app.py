"""Windows-first GUI for ZoomToText using PySide6."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import threading
from typing import TYPE_CHECKING, Optional

from .asr import ASRModel, DummyASR, WhisperASR
from .capture import list_loopback_speakers, record_until_stop_soundcard
from .pipeline import process_audio

# @TODO-8 — Import Summarizer
from .summarizer import GeminiSummarizer, Summarizer

if TYPE_CHECKING:
    from PySide6.QtCore import QObject


MODEL_OPTIONS = [
    "turbo",
    "large-v3",
    "small",
    "base",
    "tiny",
    "medium",
    "dummy",
]


@dataclass
class AppSettings:
    """Persisted GUI settings."""

    output_dir: Path
    model_name: str
    open_output_folder: bool
    open_transcript: bool
    last_input_path: str | None
    last_device_index: int | None
    # @TODO-9 — Add summarization settings
    summarize_enabled: bool
    api_key: str | None

    def to_dict(self) -> dict:
        return {
            "output_dir": str(self.output_dir),
            "model_name": self.model_name,
            "open_output_folder": self.open_output_folder,
            "open_transcript": self.open_transcript,
            "last_input_path": self.last_input_path,
            "last_device_index": self.last_device_index,
            "summarize_enabled": self.summarize_enabled,
            "api_key": self.api_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        output_dir = Path(data.get("output_dir") or (Path.cwd() / "output"))
        return cls(
            output_dir=output_dir,
            model_name=data.get("model_name") or "turbo",
            open_output_folder=bool(data.get("open_output_folder", True)),
            open_transcript=bool(data.get("open_transcript", False)),
            last_input_path=data.get("last_input_path"),
            last_device_index=data.get("last_device_index"),
            summarize_enabled=bool(data.get("summarize_enabled", False)),
            api_key=data.get("api_key") or os.environ.get("GEMINI_API_KEY"),
        )


def _settings_path() -> Path:
    return Path.home() / ".zoom_to_text" / "settings.json"


def load_settings() -> AppSettings:
    """Load persisted settings or return defaults."""
    path = _settings_path()
    if path.exists():
        try:
            return AppSettings.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return AppSettings.from_dict({})


def save_settings(settings: AppSettings) -> None:
    """Persist settings to disk."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


def _ensure_pyside6_available() -> None:
    if find_spec("PySide6") is None:
        raise RuntimeError(
            "PySide6 is required for the GUI. Install with 'pip install .[gui]' or "
            "'pip install PySide6'."
        )


def _resolve_asr(model: str) -> ASRModel:
    if model == "dummy":
        return DummyASR()
    return WhisperASR(model_name=model)


def _open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


def _build_worker(
    input_path: Path | None,
    output_dir: Path,
    model_name: str,
    *,
    live: bool,
    device: int | str | None,
    # @TODO-11 — Add summarizer parameter
    summarizer: Summarizer | None = None,
) -> "QObject":
    from PySide6.QtCore import QObject, Signal

    class TranscriptionWorker(QObject):
        # @TODO-12 — Update signal to include optional summary_path
        finished = Signal(Path, Path, object)  # transcript, metadata, summary (or None)
        error = Signal(str)
        status = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self._stop_event = threading.Event()

        def stop(self) -> None:
            self._stop_event.set()

        def run(self) -> None:
            temp_path: Path | None = None
            try:
                self.status.emit("Loading model...")
                asr = _resolve_asr(model_name)
                active_input = input_path
                if live:
                    self.status.emit("Recording system audio...")
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        temp_path = Path(tmp.name)
                    record_until_stop_soundcard(
                        temp_path,
                        device=device,
                        stop_event=self._stop_event,
                        status_callback=self.status.emit,
                    )
                    active_input = temp_path
                    self.status.emit("Transcribing recording...")
                else:
                    self.status.emit("Transcribing file...")
                if active_input is None:
                    raise RuntimeError("No input selected.")
                if summarizer is not None:
                    self.status.emit("Transcribing and summarizing...")
                transcript_path, metadata_path, summary_path = process_audio(
                    active_input, asr, output_dir, summarizer=summarizer
                )
                self.finished.emit(transcript_path, metadata_path, summary_path)
            except Exception as exc:
                self.error.emit(str(exc))
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)

    return TranscriptionWorker()


def main() -> None:
    """Launch the ZoomToText GUI."""
    _ensure_pyside6_available()
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QFileDialog,
        QStatusBar,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("ZoomToText")
            self.settings = load_settings()
            self.worker_thread: Optional[QThread] = None
            self.worker: Optional[QObject] = None

            self.input_path_edit = QLineEdit()
            if self.settings.last_input_path:
                self.input_path_edit.setText(self.settings.last_input_path)

            self.output_dir_edit = QLineEdit(str(self.settings.output_dir))
            self.model_combo = QComboBox()
            self.model_combo.setEditable(True)
            self.model_combo.addItems(MODEL_OPTIONS)
            if self.settings.model_name in MODEL_OPTIONS:
                self.model_combo.setCurrentText(self.settings.model_name)
            else:
                self.model_combo.setCurrentText(self.settings.model_name)

            self.open_output_checkbox = QCheckBox("Open output folder when complete")
            self.open_output_checkbox.setChecked(self.settings.open_output_folder)
            self.open_transcript_checkbox = QCheckBox("Open transcript when complete")
            self.open_transcript_checkbox.setChecked(self.settings.open_transcript)
            # @TODO-10 — Add summarization UI elements
            self.summarize_checkbox = QCheckBox("Generate summary after transcription")
            self.summarize_checkbox.setChecked(self.settings.summarize_enabled)
            self.api_key_edit = QLineEdit()
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.api_key_edit.setPlaceholderText(
                "Enter Gemini API key or set GEMINI_API_KEY env var"
            )
            if self.settings.api_key:
                self.api_key_edit.setText(self.settings.api_key)

            self.device_combo = QComboBox()
            self.device_combo.addItem("Default speaker", None)
            self.refresh_devices()

            self.start_file_button = QPushButton("Transcribe File")
            self.start_live_button = QPushButton("Start Live Capture")
            self.stop_live_button = QPushButton("Stop Recording")
            self.stop_live_button.setEnabled(False)

            self.status_label = QLabel("Ready")
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)

            self._build_layout()
            self._connect_signals()

        def _build_layout(self) -> None:
            tabs = QTabWidget()
            tabs.addTab(self._build_file_tab(), "File Transcription")
            tabs.addTab(self._build_live_tab(), "Live Capture")
            tabs.addTab(self._build_settings_tab(), "Settings")

            container = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(tabs)
            container.setLayout(layout)
            self.setCentralWidget(container)

            status_bar = QStatusBar()
            status_bar.addWidget(self.status_label)
            status_bar.addPermanentWidget(self.progress_bar)
            self.setStatusBar(status_bar)

        def _build_file_tab(self) -> QWidget:
            widget = QWidget()
            layout = QVBoxLayout()
            form = QFormLayout()

            browse_button = QPushButton("Browse...")
            browse_button.clicked.connect(self._browse_file)
            file_row = QHBoxLayout()
            file_row.addWidget(self.input_path_edit)
            file_row.addWidget(browse_button)

            form.addRow("Audio/Video File", file_row)
            layout.addLayout(form)
            layout.addWidget(self.start_file_button)
            widget.setLayout(layout)
            return widget

        def _build_live_tab(self) -> QWidget:
            widget = QWidget()
            layout = QVBoxLayout()
            form = QFormLayout()

            refresh_button = QPushButton("Refresh Devices")
            refresh_button.clicked.connect(self.refresh_devices)
            device_row = QHBoxLayout()
            device_row.addWidget(self.device_combo)
            device_row.addWidget(refresh_button)
            form.addRow("Loopback Speaker", device_row)
            layout.addLayout(form)
            button_row = QHBoxLayout()
            button_row.addWidget(self.start_live_button)
            button_row.addWidget(self.stop_live_button)
            layout.addLayout(button_row)
            widget.setLayout(layout)
            return widget

        def _build_settings_tab(self) -> QWidget:
            widget = QWidget()
            layout = QVBoxLayout()
            form = QFormLayout()

            browse_output_button = QPushButton("Browse...")
            browse_output_button.clicked.connect(self._browse_output_dir)
            output_row = QHBoxLayout()
            output_row.addWidget(self.output_dir_edit)
            output_row.addWidget(browse_output_button)

            form.addRow("Output Directory", output_row)
            form.addRow("ASR Model", self.model_combo)
            form.addRow("", self.open_output_checkbox)
            form.addRow("", self.open_transcript_checkbox)
            form.addRow("", self.summarize_checkbox)
            form.addRow("Gemini API Key", self.api_key_edit)

            layout.addLayout(form)
            layout.addStretch()
            widget.setLayout(layout)
            return widget

        def _connect_signals(self) -> None:
            self.start_file_button.clicked.connect(self._start_file_transcription)
            self.start_live_button.clicked.connect(self._start_live_capture)
            self.stop_live_button.clicked.connect(self._stop_live_capture)

        def _browse_file(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Select audio or video file")
            if path:
                self.input_path_edit.setText(path)

        def _browse_output_dir(self) -> None:
            path = QFileDialog.getExistingDirectory(self, "Select output directory")
            if path:
                self.output_dir_edit.setText(path)

        def _set_status(self, text: str) -> None:
            self.status_label.setText(text)

        def _set_running(self, running: bool, *, live: bool) -> None:
            self.start_file_button.setEnabled(not running)
            self.start_live_button.setEnabled(not running)
            self.stop_live_button.setEnabled(running and live)
            self.progress_bar.setVisible(running)
            if running:
                self.progress_bar.setRange(0, 0)
            else:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(0)

        def _current_output_dir(self) -> Path:
            text = self.output_dir_edit.text().strip() or str(Path.cwd() / "output")
            return Path(text)

        def _current_model(self) -> str:
            return self.model_combo.currentText().strip() or "turbo"

        def _create_summarizer(self) -> Summarizer | None:
            """Create summarizer if enabled and API key available."""
            if not self.summarize_checkbox.isChecked():
                return None
            api_key = self.api_key_edit.text().strip() or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                self._show_error(
                    "Missing API Key",
                    "Summarization requires a Gemini API key. Enter it in Settings or set GEMINI_API_KEY env var.",
                )
                return None
            return GeminiSummarizer(api_key=api_key, model="gemini-3-flash-preview")

        def refresh_devices(self) -> None:
            self.device_combo.clear()
            self.device_combo.addItem("Default speaker", None)
            try:
                speakers = list_loopback_speakers()
            except Exception as exc:
                self._show_error("Unable to list devices", str(exc))
                return
            for sp in speakers:
                label = f"{sp['index']}: {sp['name']}"
                self.device_combo.addItem(label, sp["index"])
            if self.settings.last_device_index is not None:
                index = self.device_combo.findData(self.settings.last_device_index)
                if index >= 0:
                    self.device_combo.setCurrentIndex(index)

        def _start_worker(self, worker: QObject, *, live: bool) -> None:
            self.worker_thread = QThread()
            self.worker = worker
            worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(worker.run)
            worker.finished.connect(self._on_transcription_complete)
            worker.error.connect(self._on_worker_error)
            worker.status.connect(self._set_status)
            worker.finished.connect(self.worker_thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(self.worker_thread.quit)
            worker.error.connect(worker.deleteLater)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self._set_running(True, live=live)
            self.worker_thread.start()

        def _start_file_transcription(self) -> None:
            input_text = self.input_path_edit.text().strip()
            if not input_text:
                self._show_error("Missing input", "Select an audio or video file first.")
                return
            input_path = Path(input_text)
            if not input_path.exists():
                self._show_error("Missing file", f"File not found: {input_path}")
                return
            output_dir = self._current_output_dir()
            model_name = self._current_model()
            self.settings.last_input_path = str(input_path)
            self.settings.output_dir = output_dir
            self.settings.model_name = model_name
            save_settings(self.settings)

            summarizer = self._create_summarizer()
            if self.summarize_checkbox.isChecked() and summarizer is None:
                return  # Error already shown

            worker = _build_worker(
                input_path,
                output_dir,
                model_name,
                live=False,
                device=None,
                summarizer=summarizer,
            )
            self._set_status("Preparing transcription...")
            self._start_worker(worker, live=False)

        def _start_live_capture(self) -> None:
            output_dir = self._current_output_dir()
            model_name = self._current_model()
            device = self.device_combo.currentData()
            if isinstance(device, str) and device.isdigit():
                device = int(device)
            if isinstance(device, int):
                self.settings.last_device_index = device
            else:
                self.settings.last_device_index = None
            self.settings.output_dir = output_dir
            self.settings.model_name = model_name
            save_settings(self.settings)

            summarizer = self._create_summarizer()
            if self.summarize_checkbox.isChecked() and summarizer is None:
                return  # Error already shown

            worker = _build_worker(
                None,
                output_dir,
                model_name,
                live=True,
                device=device,
                summarizer=summarizer,
            )
            self._set_status("Starting live capture...")
            self._start_worker(worker, live=True)

        def _stop_live_capture(self) -> None:
            if self.worker is None:
                return
            stop = getattr(self.worker, "stop", None)
            if callable(stop):
                stop()
                self._set_status("Stopping recording...")

        def _on_transcription_complete(
            self, transcript_path: Path, metadata_path: Path, summary_path: Path | None
        ) -> None:
            self._set_running(False, live=False)
            status = (
                "Transcription complete."
                if summary_path is None
                else "Transcription and summary complete."
            )
            self._set_status(status)
            if self.open_output_checkbox.isChecked():
                _open_path(transcript_path.parent)
            if self.open_transcript_checkbox.isChecked():
                _open_path(transcript_path)
            msg = f"Transcript:\n{transcript_path}\n\nSegments:\n{metadata_path}"
            if summary_path is not None:
                msg += f"\n\nSummary:\n{summary_path}"
            self._show_message("Complete", msg)

        def _on_worker_error(self, message: str) -> None:
            self._set_running(False, live=False)
            self._set_status("Error")
            self._show_error("Transcription failed", message)

        def _show_message(self, title: str, message: str) -> None:
            QMessageBox.information(self, title, message)

        def _show_error(self, title: str, message: str) -> None:
            QMessageBox.critical(self, title, message)

        def closeEvent(self, event) -> None:  # type: ignore[override]
            self.settings.output_dir = self._current_output_dir()
            self.settings.model_name = self._current_model()
            self.settings.open_output_folder = self.open_output_checkbox.isChecked()
            self.settings.open_transcript = self.open_transcript_checkbox.isChecked()
            self.settings.summarize_enabled = self.summarize_checkbox.isChecked()
            self.settings.api_key = self.api_key_edit.text().strip() or None
            save_settings(self.settings)
            event.accept()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(720, 420)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
