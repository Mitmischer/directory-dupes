#!/usr/bin/python3
import os
import sys
import getopt
import pickle

# Idee zum Algorithmus:
# Problem
# fl1 ist die Dateien betreffend identisch zu fl2, enthält aber zusätzlich noch zwei Unterordner fl5 und fl6, die identisch zu fl3
# und fl4 (jew.) sind. Der Algorithmus bearbeitet zuerst fl3 und fl4, sodass fl5 und fl6 verschwinden.
# ==> fl1 und fl2 werden fälschlicherweise als identisch identifiziert.

# ==> Dagegen ist weder der "UID-Algorithmus" (also Vergleich aller Nodes, eine bestimmte UID enthalten) noch
#                           Lars Algorithmus (also iterativer Vergleich aller tiefsten Knoten) gefeit.
# naiv: Hashen des ganzen Ordners und seiner Kinder, Sichern des Hashes (Cache), Vergleichen der Hashes.
#  Problem: Wie finde ich effizient Ordner mit gleichen Hashes? Vllt. mit derselben Idee wie lowest_udid/highest_udid?
#
# Idee: Ordnervergleiche sind teuer! Deswegen Cache führen mit Nodes, zu denen man identisch ist - über eine ID, die pro Node nur einmal vergeben wird
#       oder Cache mit Hashes führen.


# Nochmal von vorn:
# Idee: ursprünglicher Algorithmus und gut mit Unterordnern umgehen.
#       oder: tiefste Nodes t_i mit identischen Dateien suchen.
#             Betrachte danach die jeweiligen Väterknoten v_i.
#             !Diese können nur noch untereinander identisch und nicht identisch zu irgendwelchen anderen Ordnern sein, denn etwaigen anderen Ordnern
#              fehlt der Unterordner t_i! Ist das nutzbar?
#             Achtung! Die v_i müssen separiert werden, denn ihre t_i sind nicht zwingend untereinander identisch!
#                      Vergleiche nur diejenigen v_i, deren t_i identisch sind.
#                      Ein v_i, dessen t_i zu keinem anderen Unterordner identisch war, ist für diesen v_i einzigartig. Entferne diesen v_i vom Baum.
#             Problem: Was tun, falls die v_i mehr als Ordner haben? Dann wird die Separierung ein riesiges Chaos..

class ProgressPrinter:
    def __init__(self):
        self.total   = 0
        self.current = 0
        self.message = ""

    def print(self):
        if self.current % 500 == 0:
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


#TODO: in Ast und Blatt trennen.

class Node:
    # every node has one parent and indefinitely many children.
    # only specify a udid for leafs.
    def __init__(self, name, udid=None):
        self.name = name
        self.parent = None
        self.children = []
        # References other nodes that are equal according to fdupes
        self.udid = udid
        self.highest_udid = None
        self.lowest_udid = None

    def find_deepest_nodes(self):
        nodes = [child for child in self.children if child.children]

        deepest_nodes = []
        if nodes:
            for node in nodes:
                deepest_nodes += node.find_deepest_nodes()
            return deepest_nodes
        # self is a deepest node.
        else:
            return self

    def remove(self):
        for child in self.children:
            child.remove()

        if self.is_leaf():
            save_parent = self.parent
            self.parent = None
            save_parent.remove_if_empty(self.parent)


    def find_file(self, udid):
        # we don't have that udid.
        if udid > self.highest_udid or udid < self.lowest_udid:
            return []

        found_files = []
        # else: this node or one or more of its children-nodes hold this udid.
        for child in self.children:
            if child.is_leaf():
                if child.udid == udid:
                    found_files += [child]
            else:
                found_files += child.find_file(udid)

        return found_files

    # removes this node and every parent node that would then become empty.
    def remove_if_empty(self):
        # drop all children that seperated themselves from the tree
        self.children = [child for child in self.children if self.parent]
        if not self.children:
            save_parent = self.parent
            self.parent = None
            save_parent.remove_if_empty(self.parent)

    # recursively propagate a change in udid.
    def udid_added(self, udid):
        assert bool(self.children) # do not call on leafs
        if not self.highest_udid or udid > self.highest_udid:
            self.highest_udid = udid
        if not self.lowest_udid or udid< self.lowest_udid:
            self.lowest_udid = udid
        if self.parent:
            self.parent.udid_added(udid)

    def udid_removed(self, udid):
        assert bool(self.children) # do not call on leafs
        assert( self.lowest_udid <= udid <= self.highest_udid )

        if self.lowest_udid != udid and self.highest_udid != udid:
            return

        children = [child for child in self.children if not child.children]
        nodes = [child for child in self.children if child.children]

        # find a new lower bound if the old one was removed.
        if self.lowest_udid == udid:
            # either children or nodes is not empty
            new_lowest_udid = children[0].udid if bool(children) else nodes[0].lowest_udid
            for child in children:
                new_lowest_udid = min(new_lowest_udid, child.udid)
            for node in nodes:
                new_lowest_udid = min(new_lowest_udid, node.lowest_udid)
            self.lowest_udid = new_lowest_udid

        # find a new upper bound if the old one was removed.
        if self.highest_udid == udid:
            # either children or nodes is not empty
            new_highest_udid = children[0].udid if bool(children) else nodes[0].highest_udid # children[0] exists (see first assertion)
            for child in children:
                new_highest_udid = min(new_highest_udid, child.udid)
            for node in nodes:
                new_highest_udid = min(new_highest_udid, node.lowest_udid)
            self.lowest_udid = new_highest_udid

        if self.parent:
            self.parent.udid_removed(udid)

    def set_udid(self, udid):
        assert not self.children # call on leafs only
        save_udid = self.udid
        self.udid = udid
        self.parent.udid_added(udid)
        if save_udid:
            self.parent.udid_removed(save_udid)

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

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    # true if this node holds the same files
    # false if one of those folders holds files that the other one does not.
    # Note: The nodes have equal content, if they share one set of udids.
    # undefined if this node owns other nodes.
    def equal_content(self, node):
        # do only call on nodes that do not have any nodes.
        assert not [child for child in self.children if child.children]
        assert not [child for child in self.children if child.children]
        my_udids =    [child.udids for child in self.children]
        other_udids = [child.udids for child in node.children]

        my_udids.sort()
        other_udids.sort()

        return my_udids == other_udids

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
        if self.is_leaf():
            print(indent + self.name + ", UDID={0}".format(self.udid))
        else:
            print(indent + self.name + ", UDIDS=[{0}...{1}]".format(self.lowest_udid, self.highest_udid))
        for child in self.children:
            child.print_recursive(level+1)


    def drop_leafs(self):
        # Nodes, die keine Kinder mehr haben, löschen (rekursiv nach oben)
        #TODO: ==> sicherstellen, dass keine Ordner Leafs sind (illegal!)
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

    # sum of leaf IDs multiplied by their number, added to the subnodes' hashes, if any.
    # todo: für eine Hashfunktion sehr teuer - Cache einbauen.
    def hash(self):
        leafs = [child for child in self.children if not child.children]
        nodes = [child for child in self.children if child.children]

        sum = 0
        for leaf in leafs:
            sum += leaf.udid

        sum *= len(leafs)

        for node in nodes:
            sum += node.hash()

        return sum


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
        current_node.set_udid(unique_duplicate_id)
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

# Achtung - funktioniert so noch nicht
# Das soll später der eigentliche Algorithmus werden.
def find_equal_folders(root):
    result = ""
    # root holds the highest udid.
    highest_udid = tree.highest_udid
    for i in range(0, highest_udid+1):
        # find all nodes with this udid.
        equal_files = root.find_file(i)
        if not equal_files:
            # an earlier invocation found the parent folder's of i to be equal and moved them to the result tree.
            continue
        if len(equal_files) == 1:
            # an invocation of drop_unique_folders removed the related twin path.
            # drop the whole node! it now has a file with no duplicates that will prohibit matching
            #TODO: das stimmt so nicht für teilweises Matching (also Subset-Bestimmung).
            equal_files[0].children = None
            equal_files[0].parent.remove_if_empty()
            continue

        # check all the parent nodes for equality, pairwisely.
        parent_nodes = [child.parent for child in equal_files]
        #TODO: pairwisely - bisher nur Vergleich mit dem ersten.
        check_node = parent_nodes[0]
        identical_nodes = []
        #skip the first node.
        for i in range(1,len(parent_nodes)):
            check_node2 = parent_nodes[i]
            # make sure that the checked nodes only have leafs, no other nodes
            assert not [child for child in check_node2 if check_node2.children]

            #those folders are identical.
            if check_node.equal_content(check_node2):
                identical_nodes.append(check_node)

        # extract identical nodes and save them to the output
        check_node.path()



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
