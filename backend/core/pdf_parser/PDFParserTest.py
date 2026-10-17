from pypdf import PdfReader

reader = PdfReader("data/cv.pdf")
pages = reader.get_num_pages()

key = '/Annots'
uri = '/URI'
ank = '/A'


links = []

for page in range(pages):
    print("Current Page: {}".format(page))
    pageSliced = reader.get_page(page)
    pageObject = pageSliced.get_object()
    if ("/Annots" in pageObject.keys()):
        print(*pageObject["/Annots"])
    else:
        print("No /Annots tag on the page")
    if key in pageObject.keys():
        ann = pageObject[key]
        for a in ann:
            u = a.get_object()
            if uri in u[ank].keys():
                links.append(u[ank][uri])


# print("All links:", links)
linkedin = [l for l in links if "linkedin" in l]
# print("LinkedIn url:", linkedin[0])


