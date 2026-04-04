import os
import shutil
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from kanban.board_manager import BoardManager


class GuiTestCase(unittest.TestCase):
    """!Gui Test Case."""

    @classmethod
    def setUpClass(cls):
        """!Set up class."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """!Set up."""
        self.temp_dir = tempfile.mkdtemp(prefix='kanban_gui_tests_')
        self.board_manager = BoardManager(self.temp_dir)
        self.gui = None

    def tearDown(self):
        """!Tear down."""
        if self.gui is not None:
            self.gui.window.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
