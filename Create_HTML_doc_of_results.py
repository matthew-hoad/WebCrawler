from models import *

if __name__ == '__main__':
    with open('WebScraperResults.html', 'w') as f:
        f.write('''
        <head>
            <style>
                body {
                    background-color: #222;
                    color: #ddd;
                }
            </style>
        </head>
        <body>
        ''')
        f.write('<ul>')
        for page in WebPage.select():
            f.write(f'<li><b>{page.title}</b> - <i>{page.url}</i>')
            f.write('<ul>')
            for relationship in WebPageMTM.select().where(WebPageMTM.parent==page.id):
                child = relationship.child
                f.write(f'<li><b>{child.title}</b> - <i>{child.url}</i></li>')
            f.write('</ul>')
            f.write('</li>')
        f.write('</ul>')
        if len(DeadLink.select()) > 0:
            f.write('<p>The following links could not be found, but are linked on the website being crawled:</p><ul>')
            for dead_link in DeadLink.select():
                f.write(f'<li>{dead_link.url}</li>')
        f.write('</body>')