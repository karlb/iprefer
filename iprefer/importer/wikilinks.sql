-- SQL file for use with sqlite3 cli and data from https://danker.s3.amazonaws.com/index.html
-- Results in a table that provides pagerank rankings for wikidata qids
CREATE TABLE wikilinks (qid text PRIMARY KEY, rank float);
.mode tabs
.import '2020-11-14.allwiki.links.rank' wikilinks
