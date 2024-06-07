#!/usr/bin/python3
try:
    from qwerasdf import main
    main()
except ModuleNotFoundError:
    print("Requires prior installation. Use 'pip install .'")
