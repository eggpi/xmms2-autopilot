# xmms2-autopilot

This repository contains a few ideas I've been dabbling with in the past days
regarding making my xmms2 playlists smarter. I'm sort of happy with the results
so far, although there's a lot of experimenting left to do with parameters for
the model I used and long time usage.

Basically, what I'm trying to do here is, given a currently playing song,
recommend the next song to be added to the playlist using information taken
from previous playlist manipulation.

For example, given that I usually listen to song B after song A, and then
sometimes C and D after B (ignore numbers for now):

                  1
                 --> C
           2    /
    ... A ---> B
                \ 2
                 --> D ...

it stands to reason that, the next time I hear song A, I may want to hear B, or
even C or D next.

## Recommending songs in 6 paragraphs and a TL;DR

I attempted to model these listening patterns as a directed graph like the one
(poorly) drawn above. When song A is played,  the nodes not too far from node A
are candidates for being played next, so one of them is chosen randomly. In
this model, edges have weights that reflect how closely related two songs are
-- the weight of the edge from A to B is the number of times B has been played
after A, namely 2 --, and these weights are used to weight the probability of
choosing an individual candidate.

In the example above, the candidates for next song when A is playing would be B,
C, and D, with weights (normalized by distance to A) 2/1 = 2, 1/2 = 0.5 and
2/2 = 1, respectively. This means B is four times as likely to be chosen as C,
and twice as likely as D. I also add in a random node E into the mix, with
minimum weight among other candidates (in this case 0.5), which makes it as
likely as being chosen as C.

If traversing the neighborhood of a node N does not yield enough candidates, one
of the node's predecessors (that is, a node that has an edge leading to N) is
chosen, and the candidates taken from its neighborhood are considered as well.
The predecessor node is chosen as the one whose edge to N has the largest
weight. This strategy helps integrate new leaf nodes (that don't have a
neighborhood) into the graph faster.

In the example above, applying this strategy makes D a candidate for C, since it
is connected to C's only predecessor B.

The graph is built by using positive and negative examples of nodes that go
together. If it is determined that B could follow A, the edge A -> B is created
with weight 1 if it doesn't exist, or its weight is incremented if it exists.
Likewise, the weight is decremented (and the edge is removed when the weight
reaches 0) whenever it is determined that B should not follow A.

In the example above, if D is chosen as the next song after A, and the user
approves this choice, a positive feedback could be given, which in turn creates
an edge A -> D. This, of course, makes D's neighborhood reachable from A in the
next time we need candidates for it.

**TL;DR**: Build a directed weighted graph, songs are nodes, edges connect
songs that should follow one another. Add/increment edges with positive
feedbacks from the outside, remove/decrement with negative feedbacks. Pick next
song randomly from the neighborhood of the current song, with probabilities weighted
by edge weights and node distance.

## The code

This repository contains two files: recommend.py and autopilot.py.

reccommend.py implements the graph algorithms described above. It exposes three
main functions:

    positive(u, v)
    Add positive feedback from node u to node v in the graph.

    negative(u, v)
    Add negative feedback from node u to node v in the graph.

    next(u, default = None)
    Request a node to follow u from the graph, returns the default if none is
    found.

autopilot.py is a xmms2 client that maps playlist manipulation events to
positive and negative feedbacks, and fills the playlist with songs using the
algorithms above.

Basically, whenever a song is added to a playlist or moved inside it, that's
translated into a positive feedback from the preceding song to it. When a song
is removed, that's a negative feedback. Also, when a song is skipped right
after it started, that's a negative feedback from the preceding song to the
skipped song.

When a song starts playing, the next song is requested from the graph. If no
candidates are found, a random song from the medialib is used as default (and
added to the graph when it is added to the playlist).

autopilot.py is very much a hack/work in progress (in fact, so is everything
else in this repository), and I'd love to hear more suggestions for mapping
playlist events to feedbacks, and also making it work more like pshuffle.
