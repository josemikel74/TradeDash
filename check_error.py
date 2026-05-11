import traceback
try:
    import app
except Exception as e:
    with open("error.log", "w") as f:
        f.write(traceback.format_exc())
