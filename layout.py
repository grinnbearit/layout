import csv
import time
import argparse
import requests as r
from io import BytesIO
from PIL import Image, ImageDraw


def read_deck(filename):
    """
    reads a `decker` layout file as a csv
    and returns a single list of urls and counts
    """
    with open(filename) as fp:
        reader = csv.reader(fp)
        next(reader)            #  Skip Header row
        return [(png, int(count)) for (png, count) in reader]


def url_to_image(url):
    """
    downloads an image from scryfall,
    sleeps after the request for rate limiting
    """
    response = r.get(url)
    image = Image.open(BytesIO(response.content))
    time.sleep(0.050)
    return image


def laylines_to_images(laylines):
    """
    with a list of urls and counts, returns a sequence of Image objects
    """
    images = []
    for (png, count) in laylines:
        image = url_to_image(png)
        images.append(image)
        for _ in range(count-1):
            images.append(image.copy())
    return images


def gen_sheet():
    """
    returns a new blank sheet with padding, bleed and cutlines already drawn
    """
    white = Image.new("RGBA", (4200, 2970), "white")
    black = Image.new("RGBA", (4200 - 60, 2970 - 120), "black")
    white.paste(black, (30, 60))

    draw = ImageDraw.Draw(white)

    draw.line(((30+15-2, 0), (30+15-2, 2970)), "black", width=4)

    x = 30 + 30 + 630
    for _ in range(1, 6):
        draw.line(((x+15-2, 0), (x+15-2, 2970)), "black", width=4)
        draw.line(((x+15+30-2, 0), (x+15+30-2, 2970)), "black", width=4)
        x += 60 + 630

    draw.line(((x+15-2, 0), (x+15-2, 2970)), "black", width=4)

    draw.line(((0, 60+15-2), (4200, 60+15-2)), "black", width=4)

    y = 60 + 30 + 890
    for _ in range(1, 3):
        draw.line(((0, y+15-2), (4200, y+15-2)), "black", width=4)
        draw.line(((0, y+15+30-2), (4200, y+15+30-2)), "black", width=4)
        y += 60 + 890

    draw.line(((0, y+15-2), (4200, y+15-2)), "black", width=4)

    return white


def layout(images):
    """
    lays out resized images in a 6 x 3 grid for printing on A3
    resizes them to (630, 890)

    returns a list of sheets
    """
    chunks = [images[x:x+18] for x in range(0, len(images), 18)]

    coordinates = []

    y = 60 + 30
    for row in range(3):
        x = 30 + 30
        for col in range(6):
            coordinates.append((x, y))
            x += 630 + 60
        y += 890 + 60


    sheets = []
    for chunk in chunks:
        sheet = gen_sheet()


        for (x, y), image in zip(coordinates, chunk):
            resized = image.resize((630, 890))
            sheet.alpha_composite(resized, (x, y))

        sheets.append(sheet)

    return sheets


def layout_backs():
    """
    lays out mtg backs in a 6 x 3 grid
    """
    image = Image.open("resources/back.png")
    backs = [image.copy() for _ in range(18)]
    sheet = layout(backs)[0]
    return sheet


def _split_filename(filename):
    """
    returns (base, name) for sheets when passed a filename enabling
    prefixing.
    """
    path = filename.split("/")
    name = path[-1]
    base = "" if len(path) == 1 else "/".join(path[:-1]) + "/"
    return (base, name)


def write_sheet(filename, sheet, number):
    """
    write image sheet to disk with passed sheet number
    """
    (base, name) =  _split_filename(filename)
    sheet.save(base + "%03d_%s" % (number, name))


def write_sheets(filename, sheets):
    """
    write image sheets to disk
    """
    if len(sheets) == 1:
        sheets[0].save(filename)
    else:
        (base, name) = _split_filename(filename)
        for (idx, sheet) in enumerate(sheets):
            sheet.save(base + "%03d_%s" % (idx, name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--deck',
                        help="deck filename",
                        required=True)
    parser.add_argument('-o', "--output",
                        help="image output",
                        required=True)
    parser.add_argument('-b', '--back',
                        help="add sheet of backs",
                        action="store_true")

    args = parser.parse_args()

    laylines = read_deck(args.deck)
    images = laylines_to_images(laylines)
    sheets = layout(images)
    write_sheets(args.output, sheets)

    if args.back:
        sheet = layout_backs()
        write_sheets("back_%s" % args.output, [sheet])
