#!/usr/bin/env python3
import os
from pathlib import Path
from manr import mainwindow

if __name__ == "__main__":
    os.chdir(Path(__file__).parent / "manr")
    #mainwindow.main(["--offline"])
    mainwindow.main()

