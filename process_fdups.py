#!/usr/bin/python3

import os
import sys
import getopt
import pickle
from weakref import WeakSet

class ProgressPrinter:
    def __init__(self):
        self.total   = 0
        self.current = 0
        self.message = ""

    def print(self):
        if self.current % 500:
            sys.stdout.write("\r{0}... [{1:.2%}]".format(self.message, self.current/self.total))

    def set_total(self, total):
        self.total = total

    def add_progress(self):
        self.current += 1
        self.print()

    def reset(self):
        if self.message:
            print("\r{0}... [100.00%].".format(self.message))
        self.total = self.current = 0
        self.message = ""

    def parametrize(self, total, message):
        self.reset()
        self.total = total
        self.message = message

pprinter = ProgressPrinter()


#udid finden;
#jeder Node befragt jeden seiner Subnodes. Jeder Subnode, der ein Node ist, befragt seinerseits seine Subnodes.
#Jeder Subnode, der ein Leaf ist, gibt True zurück, falls er fündig wurde und false sonst.
#Optimierung: Jeder Node speichert nicht alle, sondern nur den größten und kleinsten Wert seiner Leafs und kann so
#schnell bestimmen, dass er einen Eintrag ganz sicher nicht enthält (nicht aber, dass er ihn bestimmt enthält.)
class Node:
    # every node has one parent and indefinitely many children.
    # only specify a udid for leafs.
    def __init__(self, name, udid=None):
        self.name = name
        self.parent = None
        self.children = []
        # References other nodes that are equal according to fdupes
        self.udids = []

    # Returns file and folder counts (recursively, top-down).
    def stats(self, file_count=0, folder_count=0):
        global pprinter
        pprinter.add_progress()

        subfolders = [child for child in self.children if child.children]
        # folders and files of this particular node.
        folder_count += len(subfolders)
        file_count += len(self.children) - folder_count
        # folders and files of this node's children and their children respective.
        for subfolder in subfolders:
            # subfolders should report their OWN counts - do not accumulate our counts.
            # therefore (0,0) (default values) and not (file_count, folder_count)
            additional_file_count, additional_folder_count = subfolder.stats()
            file_count += additional_file_count
            folder_count += additional_folder_count

        return file_count, folder_count

    def is_leaf(self):
        return not self.children

    # add udid to self and to every parent.
    # Makes this node a leaf.
    def add_udid(self, udid):
        # we can't make this node a leaf if there are children.
        #if self.children:
        #    assert(false)
        self.udids.append(udid)
        if self.parent:
            self.parent.add_udid(udid)

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def has_child(self, name):
        return name in [c.name for c in self.children]

    def get_child(self, name):
        # assuming there are no two children sharing the same name
        for child in self.children:
            if child.name == name:
                return child
        return None

    def print_recursive(self, level=0):
        indent = "  " * level
        print(indent + self.name + ", UDIDS={0}".format(self.udids))
        for child in self.children:
            child.print_recursive(level+1)

    # recursively
    # necessary as leaf removal might lead to folders being leafs. That is not legal and such folder must be purged.
    def remove_if_empty(self):
        if not self.children:
            self.parent = None


    def drop_leafs(self):
        # Nodes, die keine Kinder mehr haben, löschen (rekursiv nach oben)
        # ==> sicherstellen, dass keine Ordner Leafs sind (illegal!)
        # leaf = no children
        self.children = [c for c in self.children if c.children]

    def path(self, first_incovation=True):
        if self.parent:
            return self.parent.path(False) + "/" + self.name
        else:
            # root is special... that sucks.
            if self.name == "/":
                if first_incovation:
                    return "/"
                else:
                    return ""
            return self.name

def build_tree(lines):
    global pprinter
    folder_count = 0
    file_count = 0
    tree = Node("/")
    line_count = len(lines)
    print("{0} files to process.".format(line_count))
    discarded = 0
    unique_duplicate_id = 0

    pprinter.parametrize(line_count, "Building directory tree")
    for path in lines:
        pprinter.add_progress()
        # Create a node.
        if path.strip() == "": # empty line indicates: new set of duplicates will follow.
            unique_duplicate_id += 1
            continue

        if not path.startswith("/"):
            discarded += 1
            continue

        path = path.rstrip()
        folders = path.split("/")
        # throw away the first token ''
        folders.pop(0)
        current_node = tree
        for folder in folders:
            maybe_node = current_node.get_child(folder)
            if maybe_node:
                current_node = maybe_node
                continue
            else:
                folder_count += 1
                new_node = Node(folder)
                current_node.add_child(new_node)
                current_node = new_node
        # current_node is now a leaf.
        current_node.add_udid(unique_duplicate_id)
        folder_count -= 1
        file_count += 1

    pprinter.reset()
    print(" Note: {0} invalid files discarded.".format(discarded))

    return (file_count, folder_count, tree)


def usage():
    print("process_fdups [-h] [-c checkpoint_file]")

# recursively.
# assumes correct parametrization of pprinter.
def drop_unique_folders(node):
    global pprinter
    pprinter.add_progress()
    # also contains folder names - but filesystems demand that no "nodes (files or folders) share the same name.
    # ==> no false positives.
    children_names = [c.name for c in node.children]
    path = node.path()
    if not os.path.isdir(path):
        print("\rCannot find directory '{0}' - removing path from tree.".format(path))
        # the owning recursive call will interpret this as deletion-request.
        node.parent = None
        return

    _,_,files = next(os.walk(path))
    # alphabetische Sortierung einfuehren? Dann O(n) statt O(n²). Aber nicht erst in dieser Funktion sortieren -
    # das ist dann nicht viel billiger (?)
    for file in files:
        if not file in children_names:
            #print(file + " is not in " + str(children_names))
            # the folder contains a file that was listed as a duplicate by fdupes.
            # ==> the folder has unique content.
            node.drop_leafs()
            # the leafs are dropped, no need to look for even more unique-ness
            break

    # drop folders only
    for child in [n for n in node.children if not n.is_leaf()]:
        drop_unique_folders(child)
        # purge folders that lost all their childs and are leafs now (illegal)!
        if child.is_leaf():
            # schedule for deletion
            child.parent = None

    # only take the items that are not scheduled for deletion.
    node.children = [c for c in node.children if c.parent]



def update_checkpoint_file(file_name, state):
    #todo: tempfile und dann verschieben.
    print("Checkpoint - saving program state to disk...")
    file = open(file_name, "wb")
    pickle.dump(state, file)

def main():
    global pprinter

    tree = None
    file_count = 0
    folder_count = 0
    checkpoint_file = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:")
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt,arg in opts:
        if opt == "-h":
            usage()
            return
        elif opt == "-c":
            # open checkpoint file
            if os.path.isfile(arg):
                print("Opening checkpoint file " + str(arg))
                checkpoint_file = open(arg, "rb")
                try:
                    sys.stdout.write("Loading tree... ")
                    file_count, folder_count, tree = pickle.load(checkpoint_file)
                    print("successful.")
                    # dirty hack to make checkpoint_file a string for the call to update_checkpoint_file
                    # ==> just extract the arg here and make a new funcion load_cp_file.
                    checkpoint_file = arg
                    continue
                except:
                    print("Invalid checkpoint file.")
                    # continue below

            print("Saving checkpoints to " + str(arg))
            checkpoint_file = arg

    if not tree:
        with open("dups") as f:
            lines = f.readlines()
            file_count, folder_count, tree = build_tree(lines)
            if checkpoint_file:
                update_checkpoint_file(checkpoint_file, (file_count, folder_count, tree))

    print("{0} files.".format(file_count))
    print("{0} folders.".format(folder_count))

    print("---sanity check---")
    pprinter.parametrize(folder_count, "Counting")
    _file_count, _folder_count = tree.stats()
    pprinter.reset()

    print("{0} files.".format(_file_count))
    print("{0} folders.".format(_folder_count))


    # now a tree is loaded
    pprinter.parametrize(folder_count, "Purging unique folders")
    drop_unique_folders(tree)
    pprinter.reset()

    # just a crude approximation
    pprinter.parametrize(folder_count, "Counting")
    _file_count, _folder_count = tree.stats()
    pprinter.reset()

    print("{0} files.".format(_file_count))
    print("{0} folders.".format(_folder_count))

    update_checkpoint_file(checkpoint_file,(_file_count, _folder_count, tree))



if __name__ == "__main__":
    main()
