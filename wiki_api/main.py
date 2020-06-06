import classes
import sys

if __name__ == "__main__":

    if len(sys.argv) > 1:
        page_title = sys.argv[1]
    else:
        page_title = "National Basketball Association"

    out = classes.Getter(page_title)
    out.plot()