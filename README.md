
# MicroFlashCards
TLDR: Facilitates periodic remembering of flash card answers.

# Phased Recall
A proven method to retain new information by periodic reinforcement of recall. 
Get better memory building results than re-reading notes on a subject.

# Requirement
* Desktop replacement for Anki cards
* Be much smaller than Anki application
* Flashcards for Text only questions and answers
* Simple text interface for less distraction
* Choose difficulty level of cards in a deck when learning new subject
* Include reversible cards for learning terms and definitions
* Stores card desks in a single simple database file for easy backup.
* Use AI ( for example Claude ) to research and generate new decks and cards from public information sources for personal use

# Concepts
Decks are containers for one or more flashcard
The database file can hold many card decks
There are two types of card:
* Front Only - Recall the answer for a given question
* Reversible Definition - Write once, use both ways.
  * Recall the term used for a given definition
  * Recall the definition for a given term
There are 4 card difficulty levels:
  1. Beginner
  2. Intermediate
  3. Expert
  4. Wizard
When learning from a deck you can choose the maximum difficultly of card level for the learning session.
Cards have a hints section. During learning the optional hint is hidden until the user decides to display the hint or move directly to display the answer.
Cards have a notes section. During learning the optional notes are displayed at the same time as the answer.

# Running
In an operating system terminal or command line.
Navigate to where file 'cli.py' is downloaded to.

To use existing default or create a new default deck database in the same location run:
```bash
python3 cli.py
```

To use a different flashcard database, supply the database filepath as additional parameter on start:
```bash
python3 cli.py my_subject.db
```

To make the default database 'flashcards.db' be a separate subject database. Simply rename the default database but retain the file extension (\*.db).


# View Decks
The default screen presented when the application is started
Shows all the decks existing in database.
```
Decks
=====
  1. Rust  (96 cards, 100 due)
  2. Rust Book 01 Getting Started  (25 cards, 0 due)
  3. Rust Book 02 Programming a Guessing Game  (22 cards, 0 due)
 ...
  4. Rust Book Appendices  (112 cards, 148 due)
  5. Test  (1 cards, 1 due)
  6. Create new deck
  7. Quit
Choose: 

```

# Use Deck
```
Deck: Rust Book 03 Common Programming Concepts
==============================================
60 cards, 63 due for recall
  1. Learn
  2. Add cards
  3. Review cards
  4. Rename deck
  5. Delete deck4
  0. Back
Choose: 

```

# Learn
```
Learn: Rust Book 03 Common Programming Concepts
===============================================
Maximum difficulty:
  1. Beginner only  (39 due)
  2. Up to Intermediate  (58 due)
  3. Up to Expert  (63 due)
  4. Up to Wizard (all cards)  (63 due)
  0. Back
Choose: 

```

```Learn: Rust Book 03 Common Programming Concepts  (up to Beginner, batch 1, 39 due)
==================================================================================
What is the name for: Code that evaluates to a resulting value, such as 5 + 6, a function or macro call, or a block in curly brackets
[Enter] show answer, q to quit: 

```
Rate how easy it was to recall the information and the Card will be rescheduled

```
Learn: Rust Book 03 Common Programming Concepts  (up to Beginner, batch 1, 39 due)
==================================================================================
What is the name for: Code that evaluates to a resulting value, such as 5 + 6, a function or macro call, or a block in curly brackets
Answer: expression
Notes: Book 3.3 Functions
------------------------------------------------------------
How hard was it to remember?
  1. Very hard - again today
  2. Hard - tomorrow
  3. Medium - in 3 days
  4. Fairly easy - in 7 days
  5. Easy - in 14 days
  6. Trivial - in 28 days
  7. Quit session
Choose: 

```

# Adding Card
```
Add card to Rust Book 03 Common Programming Concepts
====================================================
Card type:
  1. FO - Front Only
  2. RD - Reversible Definition
  0. Finish adding cards
Choose: 1

Difficulty:
  1. Beginner
  2. Intermediate
  3. Expert
  4. Wizard
  0. Cancel this card

Question: foo
Answer: bar
Hint (optional, Enter to skip):
Notes (optional, Enter to skip):
```

Enter '0' to stop adding cards and return the the **use deck** view.


