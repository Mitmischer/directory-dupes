#!/usr/bin/python3

import os
import sys
import getopt
import pickle
from weakref import WeakSet

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

def build_tree(lines):
    tree = Node("/")
    line_count = len(lines)
    print("{0} files to process.".format(line_count))
    i = 0
    discarded = 0
    unique_duplicate_id = 0

    for path in lines:
        i += 1
        if not i % 500:
            percentage = (i/line_count)
            sys.stdout.write("\rBuilding directory tree... [{:.2%}]".format(percentage))
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
                new_node = Node(folder)
                current_node.add_child(new_node)
                current_node = new_node
        # current_node is now a leaf.
        current_node.add_udid(unique_duplicate_id)

    print("\rBuilding directory tree... successful.")
    print(" Note: {0} invalid files discarded.".format(discarded))

    return tree


def usage():
    print("process_fdups [-h] [-c checkpoint_file]")

def drop_unique_folders(tree):
    pass

def main():
    tree = None
    checkpoint_file = None

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hc:")
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
                    tree = pickle.load(checkpoint_file)
                    print("success.")
                    continue
                except:
                    print("Invalid checkpoint file.")
                    # continue below

            print("Saving checkpoints to " + str(arg))
            checkpoint_file = open(arg, "wb")

    if not tree:
        with open("dups") as f:
            lines = f.readlines()
            tree = build_tree(lines)
            if checkpoint_file:
                print("Checkpoint - saving tree to disk...")
                pickle.dump(tree, checkpoint_file)
            #print(len(tree.children))
    tree.print_recursive()
    # now a tree is loaded
    drop_unique_folders(tree)

if __name__ == "__main__":
    main()
