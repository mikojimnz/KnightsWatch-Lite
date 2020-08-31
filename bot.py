import discord
import json
import nltk
import numpy
import os
import pickle
import praw
import random
import re
import signal
import sys
import tensorflow
import tflearn
import time
import traceback

from nltk.stem.lancaster import LancasterStemmer
from termcolor import colored, cprint
from time import sleep

CONST_REG = r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))'

def main():
    with open("settings.json") as jsonFile1:
        cfg = json.load(jsonFile1)

    with open('training/intents.json') as jsonFile2:
        data = json.load(jsonFile2)

    with open("model/data.pickle", "rb") as p:
        words, labels, training, output = pickle.load(p)

    def bag_of_words(s, words):
        bag = [0 for _ in range(len(words))]

        s_words = nltk.word_tokenize(s)
        s_words = [stemmer.stem(word.lower()) for word in s_words]

        for se in s_words:
            for i, w in enumerate(words):
                if w == se:
                    bag[i] = 1

        return numpy.array(bag)

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')

    stemmer = LancasterStemmer()
    tensorflow.reset_default_graph()
    net = tflearn.input_data(shape=[None, len(training[0])])
    net = tflearn.fully_connected(net, 8)
    net = tflearn.fully_connected(net, 8)
    net = tflearn.fully_connected(net, len(output[0]), activation="softmax")
    net = tflearn.regression(net)
    model = tflearn.DNN(net)
    model.load("model/model.tflearn")

    reddit = praw.Reddit(cfg['praw']['cred'])
    sub = reddit.subreddit(cfg['praw']['sub'])
    commentStream = sub.stream.comments(skip_existing=cfg['praw']['skipExisting'])
    client = discord.Client()

    color = {
    "ACCEPTABLE": "green",
    "NEUTRAL": "white",
    "POSSIBLE WARNING": "red"
    }

    os.system('cls' if os.name == 'nt' else 'clear')
    cprint("\n    Ready\n", 'green')

    async def read_comments():
        await client.wait_until_ready()

        elevated_ch = client.get_channel(cfg['discord']['channels']['elevated'])
        realtime_ch = client.get_channel(cfg['discord']['channels']['realtime'])
        unsure_ch = client.get_channel(cfg['discord']['channels']['unsure'])

        try:
            for comment in commentStream:
                raw = " ".join(comment.body.lower().splitlines())
                raw = re.sub(CONST_REG, ' ', raw, flags=re.MULTILINE)
                raw = re.sub(r'([\'’])', '', raw)
                raw = re.sub(r'[^a-z\s]', ' ', raw)
                raw = re.sub(r'[ ]+', ' ', raw.strip())
                inp = re.sub(r'( x b )|( nbsp )', ' ', raw)
                user = comment.author.name
                link = comment.permalink

                if (len(inp) <= 0):
                    continue

                results = model.predict([bag_of_words(inp, words)])[0]
                results_index = numpy.argmax(results)
                tag = labels[results_index]
                confidence = results[results_index] * 100

                if (results[results_index] > cfg['model']['confidence']):
                    for tg in data["intents"]:
                        if tg['tag'] == tag:
                            classification = tg['classification']

                    await realtime_ch.send(f'**[{confidence:0.3f}% {classification}]** By: {user}\n\n```\n{comment.body}\n```\n<http://reddit.com{link}>')

                    if (classification == 'POSSIBLE WARNING'):
                        await elevated_ch.send(f'**[{confidence:0.3f}% {classification} ❗️]** By: {user}\n\n```fix\n{comment.body}\n```\n<http://reddit.com{link}>')

                    if (cfg['debug']['outputResults']):
                        print(f'\n{inp}')
                        cprint(f'\n    [{confidence:0.3f}% {classification}]', color[classification])
                        print(f'    By: {user}\n    http://reddit.com{link}\n')

                else:
                    await unsure_ch.send(f'**[UNSURE {confidence:0.3f}% {classification} ❓]** By: {user}\n\n```\n{comment.body}\n```\n<http://reddit.com{link}>')

                    if (cfg['debug']['outputResults']):
                        print(f'\n{inp}')
                        cprint(f'\n    [UNSURE {confidence:0.3f}% {tag}]', 'cyan')
                        print(f'    By: {user}\n    http://reddit.com{link}\n')

        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as e:
            print(f'EXCEPTION:\n{e}')
            sleep(10)

    @client.event
    async def on_ready():
        cprint(f'    Discord connection established, logged in as {client.user}', 'green')
        client.loop.create_task(read_comments())

    client.run(cfg['discord']['clientID'])

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if input("\nDo you really want to quit? (y/n)> ").lower().startswith('y'):
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nQuitting")
        sys.exit(1)

    signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == "__main__":
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    main()
