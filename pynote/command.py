import os
import sys
import difflib
import hashlib
import subprocess
from datetime import datetime
from prettytable import PrettyTable

from pynote import config
from pynote import container
from pynote import helper
from pynote import report


# ---------------------------------------------
# - Commands for reading and displaying notes -
# ---------------------------------------------

def list_(tags=()):
    """
    Print out a table with all notes.

    args:
        - tags:         a tuple with tags which should be
                        filtered , e.g.: ('tag1', 'tag2')

    """
    table = report.DataTable(tags)

    if table:
        print(table)
    else:
        print(_('No data!'))


def show(key, no_header=False, lang=None):
    """
    Show a specific note.

    args:
        - key:          numeric key of the note in the
                        data container
        - no_header:    supress the note header
        - lang:         specify a programming language
                        for pygments highlighting

    """
    data = container.Data()
    try:
        note = data[key]
    except IndexError:
        helper.exit_not_exists()

    # Send note.content to pygments if lang is not None.
    content = helper.highlight(note.content, lang) if lang else note.content

    if no_header:
        print(content, end='')
    else:
        print(note.get_header(), end='')
        print(content)


def show_all(no_header=False):
    """
    Print all notes in data container.

    args:
        - no_header:    supress the note header

    """
    data = container.Data()

    for i, note in enumerate(data):
        print()
        print()
        print('-- note {} --'.format(i))
        print()

        if no_header:
            print(note.content, end='')
        else:
            print(note.get_header(), end='')
            print(note.content, end='')


def trash():
    """
    Print out a table with all notes in trash.

    """
    table = report.TrashTable()

    if table:
        print(table)
    else:
        print(_('You have no data in pynote trash... :-)'))


# ----------------------------------------
# - Stuff for deleting and editing notes -
# ----------------------------------------

def new(title):
    """
    Create a new note and save it in data.json.

    """
    data = container.Data()
    note = container.Note.create(title)
    tmp_file = helper.create_tempfile()

    # Open the chosen editor to enter the content.
    # Read the entered data from the tempfile.
    subprocess.call([config.EDITOR, tmp_file])
    with open(tmp_file, 'r') as f:
        note.content = f.read().rstrip()  # Strip trailing whitespace.

    data.append(note)
    os.remove(tmp_file)


def edit(key, title=False):
    """
    Edit a note's content or title and create new revision.

    args:
        - title:        If True edit the title.

    """
    now = datetime.now()
    data = container.Data()
    revisions = container.Revisions()
    try:
        note = data[key]
    except IndexError:
        helper.exit_not_exists()
    content = note.content if title is False else note.title

    # Create the content's MD5sum to detect any changes.
    # String has to be converted to bytes before passing
    # it to hashlib.md5().
    md5_old = helper.get_md5(content)
    tmp_file = helper.create_tempfile()

    with open(tmp_file, 'w') as f:
        f.write(content)

    subprocess.call([config.EDITOR, tmp_file])

    with open(tmp_file, 'r') as f:
        content = f.read().rstrip()  # Strip trailing whitespace.

    md5_new = helper.get_md5(content)

    # Check if there are any changes.
    # Otherwise do not create a new revision.
    if md5_old != md5_new:
        # At first append the old revision to revisions.json,
        # update the note and increment the revision number.
        revisions.append(note)

        if title is False:
            note.content = content
        else:
            note.title = content
        note.updated = now
        note.revision += 1
        data[key] = note
    else:
        print(_('You have not changed anything!'))
        print(_('No new revision has been created!'))

    os.remove(tmp_file)


def delete(key):
    """
    Remove a note from data.json, increment the
    revision number and append it to trash.json.

    """
    now = datetime.now()
    data = container.Data()
    trash = container.Trash()
    try:
        note = data[key]
    except IndexError:
        helper.exit_not_exists()
    note.deleted = now

    # Just move the note from trash to data.
    # Do not create a new revision because
    # a deleted note has a deletion time.
    trash.append(note)
    del data[key]


def restore(key):
    """
    Restore a note from trash.

    """
    now = datetime.now()
    data = container.Data()
    trash = container.Trash()
    try:
        note = trash[key]
    except IndexError:
        helper.exit_not_exists()
    note.deleted = None

    # Just move the note from trash to data.
    # Do not create a new revision because
    # a deleted note has a deletion time.
    data.append(note)
    del trash[key]


# --------------------
# - Revision section -
# --------------------

def revisions(key):
    """
    Display the available revisions of a note.

    """
    data = container.Data()
    note = data[key]
    table = report.RevisionsTable(note)

    print(_("There are {} revisions of '{}':").format(len(table), note.title))
    print()
    print(table)


def compare(key, to_rev, from_rev, no_color=False):
    """
    Compare the given revisions of a note and create a unified diff.

    """
    data = container.Data()
    revisions = container.Revisions()
    note = data[key]
    uuid = note.uuid
    from_note = None
    to_note = note if note.revision == to_rev else None

    for v in revisions:
        # If to_rev is the most recent revision in data then it has
        # already been set.
        if to_note is None and (v.uuid == uuid and v.revision == to_rev):
            to_note = v
        if v.uuid == uuid and v.revision == from_rev:
            from_note = v

    # Check if both revisions have been found.  Otherwise
    # let the user know there are no revisions.
    # splitlines(keepends=True) ensures '\n' endings.
    if to_note and from_note:
        from_content = from_note.content.splitlines(keepends=True)
        to_content = to_note.content.splitlines(keepends=True)
        from_date = from_note.updated.strftime(config.DATEFORMAT)
        to_date = to_note.updated.strftime(config.DATEFORMAT)
        from_title = from_note.title + ', revision: ' + str(from_note.revision)
        to_title = to_note.title + ', revision: ' + str(to_note.revision)

        diff = difflib.unified_diff(from_content, to_content,
                                    fromfile=from_title,
                                    tofile=to_title,
                                    fromfiledate=from_date,
                                    tofiledate=to_date)

        diff = ''.join(tuple(diff))
        # REVIEW
        if no_color is False:
            diff = helper.highlight(diff, lang='diff')
        print(diff, end='')
    else:
        print(_('Error: Maybe the revisions do not exist?'))


# ---------------------
# - Commands for tags -
# ---------------------

# TODO: Maybe split up into two methods.
def tags(key=None):
    """
    Display all available tags.

    """
    data = container.Data()

    if key:
        note = data[key]
        tags = note.tags
        if tags:
            print(_('Note {}, {}, is tagged with:').format(key, note.title))
        else:
            print(_('Note {}, {}, is not tagged!').format(key, note.title))
    else:
        tags = set()
        for note in data:
            for tag in note.tags:
                tags.add(tag)
        if tags:
            print(_('The following tags exist:'))
        else:
            print(_('No tags exist!'))

    for tag in tags:
        print(tag)


def add_tags(key, tags=()):
    """
    Add tags to a note.

    """
    data = container.Data()
    note = data[key]
    for tag in tags:
        note.tags.add(tag)

    data[key] = note


def del_tags(key, tags=()):
    """
    Delete tags from a note.

    """
    data = container.Data()
    note = data[key]
    for tag in tags:
        note.tags.discard(tag)

    data[key] = note