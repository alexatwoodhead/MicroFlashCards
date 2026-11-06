"""Numbered-menu character interface for phased recall of flashcards.

Each screen follows a state in the CLAUDE.md state diagram: view_decks, new_deck,
edit_deck, rename_deck, delete_deck, add_cards, review_deck, edit_card and learn_deck
(with recall_card for one card).

Every screen starts with header(), which clears the terminal (when output is a terminal)
and shows any messages queued with notify() by the previous screen. A learning session
first asks for the maximum card difficulty, then is drawn by LearnScreen, which redraws
the screen at each step with the cards rated so far listed above the current one.

Usage: python3 cli.py [database file]
"""
import os
import random
import shutil
import sys
from pathlib import Path

from db import (ANSWER_MAX, HINT_MAX, NOTES_MAX, QUESTION_MAX, RATINGS,
                Store, ValidationError)

BATCH_SIZE = 10
DEFAULT_DB = Path(__file__).with_name("flashcards.db")

# Label shown before the prompt in a learning session, by (TypeCode, IsBack).
QUESTION_LABELS = {
    ("FO", 0): "Question:",
    ("RD", 0): "What is meant by:",
    ("RD", 1): "What is the name for:",
}
RATING_NAMES = {days: label for label, days in RATINGS}

_notices = []  # messages to show under the next screen title


class Quit(Exception):
    """End of input: leave the application."""


def ask(prompt):
    """Read one trimmed line; raise Quit on end of input or Ctrl+C."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise Quit


def is_terminal():
    """True when output goes to an interactive terminal (so the screen can be cleared)."""
    return sys.stdout.isatty()


def clear_screen():
    """Clear the terminal; when output is not a terminal, print a blank line instead."""
    if not is_terminal():
        print()
    elif os.name == "nt":
        os.system("cls")
    else:
        print("\033[2J\033[H", end="", flush=True)


def notify(message):
    """Keep a message to show under the next screen title (it would be cleared otherwise)."""
    _notices.append(message)


def header(title):
    """Clear the screen, print an underlined title and any pending messages."""
    clear_screen()
    print(f"{title}\n{'=' * len(title)}")
    while _notices:
        print(_notices.pop(0))


def choose(options, zero_label="Back"):
    """Show (label, value) options numbered from 1; return the chosen value, or None for 0."""
    for number, (label, _) in enumerate(options, 1):
        print(f"  {number}. {label}")
    print(f"  0. {zero_label}")
    while True:
        choice = ask("Choose: ")
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][1]
        print(f"Please enter a number from 0 to {len(options)}.")


def confirm(prompt, default=False):
    """Ask a yes/no question; an empty answer gives `default`."""
    answer = ask(f"{prompt} ({'Y/n' if default else 'y/N'}): ").lower()
    return default if not answer else answer in ("y", "yes")


def ask_text(label, max_len, required=False, current=None):
    """Prompt for a text field, re-asking until it is within `max_len`.

    A required field must not be blank when adding. An optional field may be skipped.
    When editing, a blank entry keeps `current` and '-' clears an optional field.
    """
    if current is not None:
        label += f" [{current}]" + ("" if required else " ('-' clears)")
    elif not required:
        label += " (optional, Enter to skip)"
    while True:
        value = ask(f"{label}: ")
        if not value:
            if current is not None or not required:
                return current
            print("This field is required.")
        elif value == "-" and not required:
            return None
        elif len(value) > max_len:
            print(f"Please keep it to {max_len} characters (you entered {len(value)}).")
        else:
            return value


def ask_question(store, deck_id, current=None, card_id=None):
    """Prompt for a question until it is not used by another card in the deck."""
    while True:
        question = ask_text("Question", QUESTION_MAX, required=True, current=current)
        if not store.question_exists(deck_id, question, card_id):
            return question
        print("That question already exists in this deck.")


def type_options(store):
    """Card types as menu options."""
    return [(f"{t['TypeCode']} - {t['TypeName']}", t["CardTypeID"]) for t in store.card_types()]


def difficulty_options(store):
    """Difficulty levels as menu options, easiest first."""
    return [(f["DifficultyName"], f["DifficultyID"]) for f in store.difficulties()]


def max_difficulty_options(counts):
    """Learn-menu options from Store.due_counts_by_difficulty(): each level with the number
    of entries due at that level or easier."""
    options = []
    for number, level in enumerate(counts):
        name = level["DifficultyName"]
        if number == 0:
            label = f"{name} only"
        elif number == len(counts) - 1:
            label = f"Up to {name} (all cards)"
        else:
            label = f"Up to {name}"
        options.append((f"{label}  ({level['UpTo']} due)", level["DifficultyID"]))
    return options


def describe_days(days):
    """Wording for a reschedule interval."""
    return {0: "again today", 1: "tomorrow"}.get(days, f"in {days} days")


# Decks

def view_decks(store):
    """Main screen: list decks with card and due counts; open, create or quit."""
    while True:
        header("Decks")
        decks = store.list_decks()
        if not decks:
            print("  (no decks yet)")
        options = [(f"{d['DeckName']}  ({d['CardCount']} cards, {d['DueCount']} due)", d["DeckID"])
                   for d in decks]
        options.append(("Create new deck", "new"))
        choice = choose(options, "Quit")
        if choice is None:
            return
        deck_id = new_deck(store) if choice == "new" else choice
        if deck_id is not None:
            edit_deck(store, deck_id)


def new_deck(store):
    """Show existing names and create a uniquely named deck; return its ID, or None if abandoned."""
    header("New deck")
    names = [d["DeckName"] for d in store.list_decks()]
    print("Existing decks: " + ", ".join(names) if names else "No existing decks.")
    while True:
        name = ask("New deck name (Enter to cancel): ")
        if not name:
            return None
        try:
            return store.create_deck(name)
        except ValidationError as error:
            print(error)


def edit_deck(store, deck_id):
    """Deck menu. Review cards is only offered when the deck has cards."""
    while True:
        deck = store.get_deck(deck_id)
        header(f"Deck: {deck['DeckName']}")
        print(f"{deck['CardCount']} cards, {deck['DueCount']} due for recall")
        options = [("Learn", learn_deck), ("Add cards", add_cards)]
        if deck["CardCount"]:
            options.append(("Review cards", review_deck))
        options += [("Rename deck", rename_deck), ("Delete deck", delete_deck)]
        action = choose(options)
        if action is None:
            return
        # Only delete_deck returns True, once the deck no longer exists.
        if action(store, deck):
            return


def rename_deck(store, deck):
    """Change the deck name to another unique name; Enter cancels."""
    while True:
        name = ask(f'New name for "{deck["DeckName"]}" (Enter to cancel): ')
        if not name:
            return
        try:
            store.rename_deck(deck["DeckID"], name)
            notify("Deck renamed.")
            return
        except ValidationError as error:
            print(error)


def delete_deck(store, deck):
    """After confirmation, delete the deck with all its cards and schedules; return True if deleted."""
    if not confirm(f'Delete deck "{deck["DeckName"]}" and its {deck["CardCount"]} card(s)?'):
        notify("Deck not deleted.")
        return False
    store.delete_deck(deck["DeckID"])
    notify(f'Deck "{deck["DeckName"]}" deleted.')
    return True


# Cards

def add_cards(store, deck):
    """Add cards one after another (type, difficulty, question, answer, optional hint and notes).

    Each saved card is scheduled for recall today. Choosing 0 at the card type finishes;
    0 at the difficulty cancels this card and starts a new one.
    """
    while True:
        header(f"Add card to {deck['DeckName']}")
        print("Card type:")
        type_id = choose(type_options(store), "Finish adding cards")
        if type_id is None:
            return
        print("Difficulty:")
        difficulty_id = choose(difficulty_options(store), "Cancel this card")
        if difficulty_id is None:
            notify("Card cancelled.")
            continue
        question = ask_question(store, deck["DeckID"])
        answer = ask_text("Answer", ANSWER_MAX, required=True)
        hint = ask_text("Hint", HINT_MAX)
        notes = ask_text("Notes", NOTES_MAX)
        try:
            store.add_card(deck["DeckID"], type_id, question, answer, hint, notes, difficulty_id)
            notify("Card saved and scheduled for recall today.")
        except ValidationError as error:
            notify(f"Card not saved: {error}")


def show_card(card):
    """Print all fields of a card."""
    print(f"Type:       {card['TypeCode']} - {card['TypeName']}")
    print(f"Difficulty: {card['DifficultyName']}")
    print(f"Question:   {card['Question']}")
    print(f"Answer:     {card['Answer']}")
    print(f"Hint:       {card['Hint'] or ''}")
    print(f"Notes:      {card['Notes'] or ''}")


def review_deck(store, deck):
    """List cards by question; show the chosen card on its own screen, then edit or delete it.

    Deleting asks for confirmation and removes the card's recall schedule too. Returns to
    the deck menu on 0, or when the deck has no cards left.
    """
    while True:
        cards = store.list_cards(deck["DeckID"])
        if not cards:
            notify("No cards left to review.")
            return
        header(f"Review: {deck['DeckName']}")
        card = choose([(f"[{c['TypeCode']} · {c['DifficultyName']}] {c['Question']}", c)
                       for c in cards])
        if card is None:
            return
        header("Card")
        show_card(card)
        action = choose([("Edit card", "edit"), ("Delete card", "delete")])
        if action == "edit":
            edit_card(store, card)
        elif action == "delete":
            if confirm("Delete this card and its recall schedule?"):
                store.delete_card(card["CardID"])
                notify("Card deleted.")


def edit_card(store, card):
    """Change each field in turn and save after confirmation.

    0 at the card type or difficulty keeps the current one; Enter keeps a text field and
    '-' clears an optional one. The outcome is shown on the next screen.
    """
    header("Edit card")
    print(f"Card type (currently {card['TypeCode']}):")
    type_id = choose(type_options(store), f"Keep {card['TypeCode']}") or card["CardTypeID"]
    print(f"Difficulty (currently {card['DifficultyName']}):")
    difficulty_id = (choose(difficulty_options(store), f"Keep {card['DifficultyName']}")
                     or card["DifficultyID"])
    print("Press Enter to keep the current value.")
    question = ask_question(store, card["DeckID"], card["Question"], card["CardID"])
    answer = ask_text("Answer", ANSWER_MAX, required=True, current=card["Answer"])
    hint = ask_text("Hint", HINT_MAX, current=card["Hint"])
    notes = ask_text("Notes", NOTES_MAX, current=card["Notes"])
    if not confirm("Save changes?", default=True):
        notify("Changes discarded.")
        return
    try:
        store.update_card(card["CardID"], type_id, question, answer, hint, notes, difficulty_id)
        notify("Card updated.")
    except ValidationError as error:
        notify(f"Card not updated: {error}")


# Learning

def question_label(type_code, is_back):
    """Label for the prompt of a recall entry; 'Question:' for unknown combinations."""
    return QUESTION_LABELS.get((type_code, int(is_back)), "Question:")


def shorten(text, width):
    """Cut `text` to `width` characters, ending with an ellipsis when cut."""
    return text if len(text) <= width else text[:max(width - 1, 0)] + "…"


def rule():
    """Horizontal separator line: up to 60 characters, never wider than the terminal."""
    return "-" * min(shutil.get_terminal_size().columns, 60)


def visible_history(history, room):
    """The most recent history lines that fit in `room` lines, with a marker for the rest."""
    if room <= 0 or not history:
        return []
    if len(history) <= room:
        return list(history)
    keep = room - 1
    hidden = len(history) - keep
    return [f"  … {hidden} earlier"] + (history[-keep:] if keep else [])


class LearnScreen:
    """Learning session display: redrawn at each step with the rated cards listed above.

    The title shows the batch number and how many entries are still due. Rated entries are
    listed under 'Completed', trimmed to the terminal height, above the current card.
    When output is not a terminal nothing is cleared, and only lines not yet printed
    for the current card are printed, so piped output reads like a plain transcript.
    """

    def __init__(self, deck_name, level):
        self.deck_name = deck_name
        self.level = level  # name of the maximum difficulty, shown in the title
        self.history = []
        self.batch = 0
        self.due = 0
        self._printed = 0  # lines of the current card already printed (non-terminal only)
        self._titled = False

    def new_card(self):
        """Start drawing a new card (or a new message) below the history."""
        self._printed = 0

    def add(self, item, days):
        """Record a rated recall entry as one history line."""
        width = shutil.get_terminal_size().columns
        rating = f" → {RATING_NAMES.get(days, days)} ({describe_days(days)})"
        prompt = item["Question"] if not item["IsBack"] else item["Answer"]
        text = f"{question_label(item['TypeCode'], item['IsBack'])} {prompt}"
        self.history.append("  " + shorten(text, width - 2 - len(rating)) + rating)

    def redraw(self, lines=(), reserve=1):
        """Show title, history and the current card's `lines`; `reserve` lines are left for prompts."""
        if not is_terminal():
            if not self._titled:
                header(f"Learn: {self.deck_name}  (up to {self.level})")
                self._titled = True
            elif not self._printed:
                print()
            for line in lines[self._printed:]:
                print(line)
            self._printed = len(lines)
            return
        header(f"Learn: {self.deck_name}  (up to {self.level}, batch {self.batch}, {self.due} due)")
        if self.history:
            room = shutil.get_terminal_size().lines - 2 - 2 - len(lines) - reserve
            print("Completed")
            for line in visible_history(self.history, room):
                print(line)
            print(rule())
        for line in lines:
            print(line)


def recall_card(screen, item):
    """Run one recall entry through question, hint and answer on `screen`.

    The prompt label comes from question_label(). The hint step is only for the front side
    of a card with a hint. Returns the days to reschedule, or None to quit the session.
    """
    front = not item["IsBack"]
    prompt, answer = (item["Question"], item["Answer"]) if front else (item["Answer"], item["Question"])
    screen.new_card()
    lines = [f"{question_label(item['TypeCode'], item['IsBack'])} {prompt}"]
    if front and item["Hint"]:
        screen.redraw(lines)
        if ask("[Enter] show hint, q to quit: ").lower() == "q":
            return None
        lines.append(f"Hint: {item['Hint']}")
    screen.redraw(lines)
    if ask("[Enter] show answer, q to quit: ").lower() == "q":
        return None
    lines.append(f"Answer: {answer}")
    if item["Notes"]:
        lines.append(f"Notes: {item['Notes']}")
    lines.append(rule())
    lines.append("How hard was it to remember?")
    screen.redraw(lines, reserve=len(RATINGS) + 2)
    return choose([(f"{label} - {describe_days(days)}", days) for label, days in RATINGS],
                  "Quit session")


def learn_deck(store, deck):
    """Learning session over the deck's due recall entries.

    First the user picks the maximum difficulty; only cards at that level or easier are
    asked for the rest of the session. Entries are asked in random batches of BATCH_SIZE.
    Each rating reschedules the entry; 'very hard' (0 days) keeps it due today and asks it
    again later in the batch. After a batch the user may continue while entries are still
    due. The screen is redrawn at each step, with the cards rated so far listed above the
    current one.

    When every due entry is done the summary stays on screen until Enter is pressed.
    Nothing due (at all or up to the chosen level), cancelling or stopping between batches
    returns to the deck menu, where the reason is shown.
    """
    if not store.due_recalls(deck["DeckID"]):
        notify("No cards are due for recall.")
        return
    header(f"Learn: {deck['DeckName']}")
    print("Maximum difficulty:")
    counts = store.due_counts_by_difficulty(deck["DeckID"])
    max_level = choose(max_difficulty_options(counts))
    if max_level is None:
        notify("Learning session cancelled.")
        return
    level = next(c["DifficultyName"] for c in counts if c["DifficultyID"] == max_level)
    due = store.due_recalls(deck["DeckID"], max_level)
    if not due:
        notify(f"No cards up to {level} are due for recall.")
        return
    screen = LearnScreen(deck["DeckName"], level)
    while due:
        screen.batch += 1
        screen.due = len(due)
        queue = random.sample(due, min(BATCH_SIZE, len(due)))
        while queue:
            item = queue.pop(0)
            days = recall_card(screen, item)
            if days is None:
                notify("Learning session cancelled.")
                return
            store.reschedule(item["CardID"], item["IsBack"], days)
            screen.add(item, days)
            if days == 0:
                queue.append(item)  # very hard: ask again later this session
            else:
                screen.due -= 1
        due = store.due_recalls(deck["DeckID"], max_level)
        screen.due = len(due)
        if due:
            screen.new_card()
            screen.redraw([f"{len(due)} more card(s) due."])
            if not confirm("Continue?", default=True):
                notify(f"Learning session ended with {len(due)} card(s) still due.")
                return
    screen.new_card()
    screen.redraw([f"All due cards up to {level} recalled. Well done!"])
    ask("[Enter] back to the deck menu: ")


def main():
    """Open the database given on the command line (or the default) and show the decks."""
    store = Store(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB)
    try:
        view_decks(store)
    except Quit:
        print()
    finally:
        store.close()


if __name__ == "__main__":
    main()
