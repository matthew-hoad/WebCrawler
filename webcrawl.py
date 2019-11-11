from urllib.request import urlopen as request
from urllib.error import HTTPError
from time import sleep
from bs4 import BeautifulSoup as bs
from peewee import *
from models import *
import pickle, os
import create_db



def update_pickle(ROOT_URL, url_stack,keepgoing,at_start,next_url,loops):
    # create a dictionary containing the internal state of the crawler
    state = {
        'ROOT_URL': ROOT_URL,
        'url_stack': [[i[0], i[1].id] for i in url_stack],
        'keepgoing': keepgoing,
        'at_start': at_start,
        'next_url': [next_url[0], next_url[1].id],
        'loops': loops
    }
    # save down to a pickle file
    with open('webcrawlersavestate.pickle', 'wb') as f:
        pickle.dump(state, f)

def load_pickle():
    # I have made my peace with this error handling and I suggest you do the same.
    try:
        with open('webcrawlersavestate.pickle', 'rb') as f:
            # try to rebuild the stack of urls and return the recovered state of the crawler
            state = pickle.load(f)
            url_stack_rebuilt = [[i[0], WebPage.select().where(WebPage.id == i[1])[0]] for i in state['url_stack']]
            return state['ROOT_URL'], url_stack_rebuilt, state['keepgoing'], state['at_start'], [state['next_url'][0], WebPage.select().where(WebPage.id == state['next_url'][1])[0]], state['loops']
    except:
        pass

def crawler_loop():
    resuming = False
    # if a save file exists, ask if you want to load it
    # saying no when a save file exists WILL OVERWRITE your previous save file/pickle
    if os.path.isfile('webcrawlersavestate.pickle'):
        resume_dict = {'y': True, 'n': False}
        resuming_string = ''
        # if the user said something that's not y or n,
        # give out to them and tell them to try again
        while resuming_string.lower() not in ['y', 'n']:
            resuming_string = input("A previous saved state was detected. Would you like to resume where you left off? (y/n): ")
            if resuming_string.lower() not in ['y', 'n']:
                print('Invalid input, try again.')
        # use the resume_dict to return a boolean instead of a string
        resuming = resume_dict[resuming_string.lower()]
    if resuming:
        try: # to load the save file
            ROOT_URL, url_stack, keepgoing, at_start, next_url, loops = load_pickle()
        except Exception as e:
            # if resuming failed, it failed. Whaddyagonnado?
            print(f"Resuming failed: {e}")
            raise(e)
    else:
        # if not resuming, start from a clean slate.
        # Create a new DB
        create_db.clean_db_install()
        # Ask for the root URL of the website to be crawled
        ROOT_URL = input("The root url of the website (eg https://google.ie): ")
        # initialise starting values for state variables
        url_stack = []
        keepgoing = True
        at_start = True
        next_url = ["", None]
        loops = 0
    while keepgoing: # begin looping
        if not at_start:
            try:
                # take the first url and pop it off the list
                next_url = url_stack[0]
                url_stack = url_stack[1:]
            except:
                keepgoing = False
                continue
        # if there is already a webpage with this url in the db
        if len(WebPage.select().where(WebPage.url == bytes(next_url[0], 'iso-8859-9').decode("utf-8", "strict"))) > 0:
            # create a relationship between the page we found the link on, and the page the link goes to 
            WebPageMTM.create(parent=next_url[1], child=WebPage.select().where(WebPage.url == bytes(next_url[0], 'iso-8859-9').decode("utf-8", "strict"))[0])
            # if we exhausted the list of urls to go to, then stop looping
            if len(url_stack) == 0:
                keepgoing = False
            continue
        try:
            # attempt to get the page for this url
            response = request(ROOT_URL+bytes(next_url[0], 'iso-8859-9').decode("utf-8", "strict"))
            # take a snooze so the webserver doesn't fall over
            sleep(0.1)
        except HTTPError as e:
            # if there's an error, put it in the deadlinks table and note the response code (error type)
            print(f'Encountered a {response.getcode()} error (dead link): {e}')
            if len(DeadLink.select().where(DeadLink.url == next_url[0])) == 0:
                DeadLink.create(linklocation=next_url[1], url=next_url[0], responsecode=response.getcode())
            # if we exhausted the list of urls to go to, then stop looping
            if len(url_stack) == 0:
                keepgoing = False
            continue
        except Exception as e:
            # if it wasn't a http error, then it was probably an encoding issue in the url, fada, grav, accent, symbols? I tried
            print(f"Error trying to make the request: {e}")
            print(next_url[0].encode('utf-8'))
        
        # get the unique links for the output that reports how far along we are into the urls
        unique_link_urls = [i[0] for i in url_stack] + [page.url for page in WebPage.select()] + [page.url for page in DeadLink.select()]
        unique_links = len(list(set(unique_link_urls)))
        visited_links = len(WebPage.select())
        if unique_links > 0:
            print(f'{visited_links}/{unique_links} ({int(100*visited_links/unique_links)}% of unique discovered links visited)')
        try:
            # if the server returned a 200 (all good, got a response)
            if response.getcode() == 200:
                # if the page doesn't exist in the webpage table yet
                if len(WebPage.select().where(WebPage.url==next_url[0])) == 0:
                    # if it's an actual webpage (it's not a pdf, pptx, etc)
                    if 'text/html' in response.headers['Content-Type']:
                        # get the body content for the page
                        page_body = bs(str(response.read()),features="html.parser")
                        # create an entry in the webpage table for the page
                        thispage = WebPage.create(title=page_body.title.string, url=next_url[0])
                        # start parsing the body to find more links
                        for link in page_body.find_all('a'):
                            href = link.get('href')
                            if href is not None:
                                # if the link isn't empty, or just a hashtag, and it starts with the root url (i.e. it doesn't lead to another website)
                                if (href != '#' and href.startswith('/')) or href.startswith(ROOT_URL):
                                    # add the url to the stack or urls to check out!
                                    url_stack.append([href, thispage])
                    # if it's not an actual html webpage, log the page, just don't parse the body
                    else:
                        thispage = WebPage.create(title=next_url[0].split('/')[-1], url=next_url[0])
                # if the page already exists in the db
                else:
                    # move on to the next page
                    thispage = WebPage.select().where(WebPage.url==next_url[0])[0]
                # if there is a next_url and there isn't already a relationship between this page and the next url, create it
                if next_url[1] is not None and len(WebPageMTM.select().where(WebPageMTM.parent==next_url[1] and WebPageMTM.child==thispage)) == 0:
                    WebPageMTM.create(parent=next_url[1], child=thispage)
            # if the response code wasn't an all-clear
            else:
                # print an error about it
                print(f"Something went wrong. Response code {response.getcode()}.\nHeaders: {response.headers}\nUrl: {ROOT_URL+next_url[0]}")
            # if this was the first go around, it no longer is
            if at_start == True:
                at_start = False
            loops += 1
        # if something went wrong along the way, put some debug info in the console
        except Exception as e:
            print(
                next_url
            )
            print(e)
        # if we still have urls to visit
        if next_url[1] is not None:
            # update the pickle/save file
            update_pickle(ROOT_URL, url_stack, keepgoing, at_start, next_url, loops)
        # if we don't
        if len(url_stack) == 0:
            # delete the pickle/save file, we don't need it anymore
            keepgoing = False
            try:
                os.remove('webcrawlersavestate.pickle')
            except:
                print("couldn't find the pickle file when trying to delete it...")


if __name__ == '__main__':
    crawler_loop()