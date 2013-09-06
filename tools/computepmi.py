#!/usr/bin/env python3


from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import sys
from math import log

from collections import defaultdict

def pmi(sentences1, sentences2,discount = 0):
    jointcount = len(sentences1 & sentences2) - discount
    if jointcount <= 0: return None
    return log( jointcount / (len(sentences1) * len(sentences2))), jointcount+discount

def npmi(sentences1, sentences2,discount=0):
    jointcount = len(sentences1 & sentences2) - discount
    if jointcount <= 0: return None
    return log( jointcount / (len(sentences1) * len(sentences2))) / -log(jointcount), jointcount+discount

def main():
    parser = argparse.ArgumentParser(description="Simple cooccurence computation", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f','--inputtext', type=str,help="Input file (plaintext, tokenised, utf-8, one sentence per line)", action='store',default="",required=True)
    parser.add_argument('-u','--unidirectional', help="Compute unidirectionally, i.e. the left word will always occur before the right word", action='store_true',default=False)
    parser.add_argument('-s','--sorted', help="Output sorted by co-occurrence score", action='store_true',default=False)
    parser.add_argument('-t','--threshold', help="Joined occurrence threshold, do not consider words occuring less than this", type=int, action='store',default=1)
    parser.add_argument('-a','--adjacency', help="Compute the adjacency fraction (how many co-occurrence are immediate bigrams)", action='store_true',default=False)
    parser.add_argument('-A','--discountadjacency', help="Do not take immediately adjacent fragments (bigrams) into account when computing mutual information (requires -a)", action='store_true',default=False)
    parser.add_argument('--pmi',help="Compute pointwise mutual information", action='store_true',default=False)
    parser.add_argument('--npmi',help="Compute normalised pointwise mutual information", action='store_true',default=False)

    args = parser.parse_args()
    if not args.pmi and not args.npmi:
        args.pmi = True

    index = defaultdict(list)
    reverseindex = defaultdict(set)
    s_index = defaultdict(set)

    f = open(args.inputtext,'r',encoding='utf-8')
    for i, line in enumerate(f):
        sentence = i + 1
        print("Indexing @" + str(sentence),file=sys.stderr)
        if line:
            for pos, word in enumerate(line.split()):
                if word:
                    index[word].append( (sentence,pos) )
                    s_index[word].add( sentence )
                    reverseindex[sentence].add((pos,word))
    f.close()

    l = len(index)
    adjacent = defaultdict(lambda: defaultdict(int))
    if args.adjacency:
        for i, word in enumerate(index):
            print("Computing adjacency @" + str(i+1) + "/" + str(l),file=sys.stderr)
            for sentence in index[word]:
                for pos2, word2 in reverseindex[sentence]:
                    if pos2 == pos + len(word.split()) or (not args.unidirectional and pos == pos2 + len(word2.split())):
                        adjacent[word][word2] += 1

    output = []
    #compute co-occurence
    for i, word in enumerate(index):
        print("Computing mutual information @" + str(i+1) + "/" + str(l) + ": \"" + word + "\" ... occurs in " + str(len(index[word])) + " sentences",file=sys.stderr)
        for sentence, pos in index[word]:
            for pos2, word2 in reverseindex[sentence]:
                if args.unidirectional and pos2 < pos:
                    continue
                if (pos != pos2) or (word != word2):
                    adjcount = 0
                    if args.adjacency:
                        if word in adjacent and word2 in adjacent[word]:
                            adjcount = adjacent[word][word2]
                    if args.pmi:
                        score, jointcount = pmi(s_index[word], s_index[word2], adjcount if args.discountadjacency else 0 )
                    elif args.npmi:
                        score, jointcount = npmi(s_index[word], s_index[word2], adjcount if args.discountadjacency else 0 )
                    if not (score is None) and jointcount >= args.threshold:
                        if args.sorted:
                            outputdata = (word,word2,score, jointcount, adjcount / jointcount if args.adjacency else None)
                            output.append(outputdata)
                        else:
                            if args.adjacency:
                                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount) + "\t" + str(adjcount / jointcount))
                            else:
                                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount))
            break #prevent duplicates if the same word occurs multiple times in a sentence

    del index
    del reverseindex
    del adjacent

    if args.sorted:
        print("Outputting...",file=sys.stderr)
        for word,word2,score,jointcount,adjratio in sorted(output, key=lambda x: -1 * x[2]):
            if adjratio:
                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount) + "\t" + str(adjratio))
            else:
                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount))



if __name__ == '__main__':
    main()
