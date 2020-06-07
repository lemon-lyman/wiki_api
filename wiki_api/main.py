import classes
import sys

if __name__ == "__main__":

    page_title = "National Basketball Association"

    if len(sys.argv) == 3:
        page_title = sys.argv[1]
        request_size = sys.argv[2]
        out = classes.Getter(page_title, request_size=request_size)
    elif len(sys.argv) == 2:
        page_title = sys.argv[1]
        out = classes.Getter(page_title)
    else:
        out = classes.Getter(page_title)

    print(out)
    out.plot()