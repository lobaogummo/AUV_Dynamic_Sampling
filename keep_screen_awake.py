import ctypes
import time


INTERVAL_SECONDS = 30
PIXELS = 80


def move_mouse(dx, dy):
    ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)


def main():
    print("Mantendo o ecra acordado. Prima Ctrl+C para parar.")
    direction = 1

    try:
        while True:
            move_mouse(PIXELS * direction, 0)
            time.sleep(0.2)
            move_mouse(-PIXELS * direction, 0)
            direction *= -1
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nParado.")


if __name__ == "__main__":
    main()
