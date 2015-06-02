__author__ = 'lars'

from functools import reduce
from collections import Counter
from hashlib import md5
import os
class Tree:
    def __init__(self,root):
        """
        :param root: root Node
        :rtype : Tree
        """
        self.root=root

    def search(self,path):
        """
        :param path: a list of filenames
        :rtype: Node
        """
        return self.root.dfs_path(path)

    def insert(self,node):
        """
        Inserts a node into the tree, a correct structure of parent nodes for the path is created automatically
        :param node: Node
        :rtype: None
        """
        self.root.dfs_insert(node)

    def treeshake(self):
        """
        takes a look at all nodes in the tree and checks wether they are potential duplicates
        :rtype: None
        """
        self.root.dfs_treeshake()

    def create_checksums(self):
        """
        looks at all nodes in the tree,
        if the node is a potential duplicate, a valid checksum is created
        if the node is no potential duplicate, -1 is hashed as checksum
        :rtype: None
        """
        self.root.dfs_create_checksums()

    def generate_checksum_list(self):
        """
        returns a list of all valid checksums in the tree
        :rtype: []
        """
        return self.root.dfs_generate_checksum_list([])

    def find_toplevel_duplicates(self,filename):
        """
        :param filename: the name of an existing file to be overwritten with information about duplicates
        :rtype: None
        """

        self.treeshake()
        self.create_checksums()
        checksum_list=self.generate_checksum_list()
        duplicate_checksums=[x for x, y in Counter(checksum_list).items() if y > 1]

        #this dictionary contains checksums as keys and for each key a list of nodes with this checksum
        duplicates={}

        if duplicate_checksums:
            print("there are folders or files with the same checksum")

            # traverse the tree, each node compares its own checksum to the list of duplicate checksums
            duplicates=self.root.dfs_find_toplevel_duplicates(duplicate_checksums,duplicates, True)

            #write results to file
            file=open(filename,"w")
            for key in duplicates:
                duplicates[key].sort(key=lambda tuple:tuple[0],reverse=True)
                if duplicates[key][0][0]==False:
                    continue
                print("a set of dups",file=file)
                for value in duplicates[key]:
                    (toplevel,node)=value
                    if toplevel:
                        print("/".join(node.path)+"/"+node.name,file=file)
                    else:
                        print("non-toplevel occurences: "+"/".join(node.path)+"/"+node.name,file=file)

                print("-----------------------",file=file)

        return duplicates


    def find_all_duplicates(self,filename):
        """
        :param filename: the name of an existing file to be overwritten with information about duplicates
        :rtype: None
        """

        self.treeshake()
        self.create_checksums()
        checksum_list=self.generate_checksum_list()
        duplicate_checksums=[x for x, y in Counter(checksum_list).items() if y > 1]

        #this dictionary contains checksums as keys and for each key a list of nodes with this checksum
        duplicates={}

        if duplicate_checksums:
            print("there are folders or files with the same checksum")

            for dup_checksum in duplicate_checksums:
                duplicates[dup_checksum]=[]
                self.root.dfs_search_for_checksum(dup_checksum,duplicates[dup_checksum])

        file=open(filename,"w")
        for key in duplicates:
            print("a set of dups",file=file)
            for value in duplicates[key]:
                print("/".join(value.path)+"/"+value.name,file=file)

            print("-----------------------",file=file)

        return duplicates


    def print_graphml(self,filename):
        """
        :param filename: name of an existing file to be overwritten with a graph in graphml format
        :rtype: None
        """
        file=open(filename,"w")
        print("""<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns
     http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
  <graph id="G" edgedefault="undirected">""",file=file)

        self.root.dfs_print_graphml(file)

        print("""</graph>
</graphml>""",file=file)

        file.flush()
        file.close()

    def print_graphdot(self,filename):
        """
        :param filename: name of an existing file to be overwritten with a graph in graphdot format
        :rtype: None
        """
        file=open(filename,"w")
        print("""digraph filesystem {""",file=file)

        self.root.dfs_print_graphdot(file)

        print("""}""",file=file)
        file.flush()
        file.close()



class Node:
    def __init__(self, isFile, path, name, id):
        """

        :param isFile: has this been found by fdupes ? is it a file ?
        :param path: a list of foldernames as strings
        :param name: name of this file/folder
        :param id: if this was found by fdupes, set to correct id, -1 otherwise
        :rtype : Node
        """
        self.isFile=isFile
        self.path=path
        self.name=name
        self.id=id
        self.children=[]

        #so far, we don't know anything about this node
        self.potentialDup=True
        self.checksum=None


    def dfs_insert(self,node):
        """
        inserts the node into the tree and creates a correct structure of nodes for the path
        :param node:Node to be inserted into the tree
        :type node: None
        """
        node_path=node.path.copy()

        # search for the path in the tree, it's not going to exist completely
        # this method returns the "longest match"
        current_node=self.dfs_search_for_partial_path(node_path)

        # get the path that was found
        partial_path=current_node.path.copy()
        partial_path.append(current_node.name)

        # this is the rest, which has to be created by hand
        path_rest=node_path[len(partial_path):len(node_path)]

        current_path=partial_path

        for elem in path_rest:
            temp_node=Node(False,current_path,elem,-1)
            current_node.children.append(temp_node)
            current_node=temp_node
            current_path=current_path+[elem]

        current_node.children.append(node)

    def dfs_search_for_checksum(self,checksum,dups_list):
        """
        compares the checksum of all nodes (dfs) with this checksum, each math is appended to the list
        :param checksum: checksum string, already digested
        :param dups_list: list of nodes with this checksum
        :rtype: []
        """
        if self.checksum.digest()==checksum:
            dups_list.append(self)
        for child in self.children:
            dups_list=child.dfs_search_for_checksum(checksum,dups_list)
        return dups_list

    def dfs_find_toplevel_duplicates(self,checksum_list, duplicates, toplevel):
        """
        compares the checksum of all nodes (dfs) to the checksum_list,
        if a match is found, the dfs continues
        all duplicates are appended to the dict, but the toplevel dups are marked as such
        :param duplicates: a dict of duplicates
        :param checksum_list: a list of duplicate checksums
        :param toplevel: boolean flag, is this inside of a duplicate, or outside
        :rtype:{}
        """
        checksum_string=self.checksum.digest()

        if checksum_string in checksum_list:
            if checksum_string in duplicates:
                duplicates[checksum_string].append((toplevel,self))
            else:
                duplicates[checksum_string]=[(toplevel,self)]

            # this is the most toplevel duplicate, still look at all the other files
            for child in self.children:
                duplicates=child.dfs_find_toplevel_duplicates(checksum_list,duplicates, False)
        else:
            # no duplicate found so far, lets continue the dfs
            for child in self.children:
                duplicates=child.dfs_find_toplevel_duplicates(checksum_list,duplicates, True)
        return duplicates

    def dfs_search_for_path(self,path):
        """
        returns the node that matches this path
        :param path: a list of filenames as strings
        :rtype: Node
        """
        if self.name!=path[0]:
            raise Exception("the dfs has led to a problem")
        elif len(path)>1:
            folder=path[1]
            for child in self.children:
                if folder==child.name:
                    return child.dfs_search_for_path(path[1:len(path)])
            raise Exception("the path does not exist in the tree")
        else:
            return self

    def dfs_search_for_partial_path(self,path):
        """
        returns the longest slice of the path that exists in this tree as a node
        :param path: a list of filenames as strings
        :rtype: Node
        """
        if self.name!=path[0]:
            raise Exception("the dfs has led to a problem")
        elif len(path)>1:
            folder=path[1]
            for child in self.children:
                if folder==child.name:
                    return child.dfs_search_for_partial_path(path[1:len(path)])
            return self
        else:
            return self

    def dfs_create_checksums(self):
        """
        computes a checksum for all nodes
        :rtype: None
        """
        if self.children==[]:
            self.checksum=md5()
            self.checksum.update(str(self.id).encode("utf-8"))
            return

        else:
            children_checksums=[]
            for child in self.children:
                child.dfs_create_checksums()
                children_checksums.append(child.checksum.digest())

            if self.potentialDup:
                children_checksums.sort()
                self.checksum=md5()
                for child_checksum in children_checksums:
                    self.checksum.update(child_checksum)
                return
            else:
                #this is not a duplicate, give it a checksum no duplicate could have, so that it is not accidentally found
                self.checksum=md5()
                self.checksum.update(str(-1).encode("utf-8"))

    def dfs_print_graphml(self,file):
        """
        prints the graphml data of this node to the file
        :param file: file which contains the data for this tree
        :rtype: None
        """
        print("<node id=\""+self.name+"\" />",file=file)
        for child in self.children:
            child.dfs_print_graphml(file)
            print("<edge source=\""+self.name+"\" target=\""+child.name+"\"/>",file=file)

    def dfs_print_graphdot(self,file):
        """
        prints the graphdot data of this node to the file
        :param file: file which contains the data for this tree
        :rtype: None
        """
        for child in self.children:
            #print(("".join(self.path)+self.name).replace("/","_").replace("\n","")+"->"+("".join(child.path)+child.name).replace("/","_").replace("\n","")+";",file=file)
            print("\""+"/".join(self.path)+"/"+self.name+"\""+"->"+"\""+"/".join(child.path)+"/"+child.name+"\"",file=file)
            #print("\""+self.name+"\""+"->"+"\""+child.name+"\"",file=file)
            child.dfs_print_graphdot(file)

    def dfs_treeshake(self):
        """
        Check if this could potentially be a duplicate.
        Return True if yes, False otherwise
        """
        # if this is a file, found by fdupes, it can be a duplicate
        if self.isFile:
            return True

        # if the folder contains a subfolder which is not a duplicate, it isn't a duplicate itself
        for child in self.children:
            if not child.dfs_treeshake():
                self.potentialDup=False

        # each child in the tree was created by fdupes and is a potential duplicate
        # if there are more subfolders / files in this dir than there are children, this is not a duplicate
        num_files=os.listdir("/".join(self.path)+"/"+self.name+"")
        print(os.listdir("/".join(self.path)+"/"+self.name+""))
        if len(num_files)>len(self.children):
            self.potentialDup=False
            return False

        return self.potentialDup

    def dfs_generate_checksum_list(self,checksum_list):
        """
        generates a list of all the checksums of nodes in the tree which are potential checksums
        :param checksum_list: a list of all checksums computed so far, call with an empty list
        :rtype: []
        """
        for child in self.children:
            child.dfs_generate_checksum_list(checksum_list)

        # only if this is a potential duplicate, check its filesum
        if self.potentialDup:
            checksum_list.append(self.checksum.digest())
        return checksum_list



if __name__=="__main__":

    # attention:
    # the treeshake algorithm only works for real files and folders
    # therefore only the printing as graphs is tested


    print("testing the tree")
    root=Node(False,[],"sample 2",-1)
    tree=Tree(root)
    for i in range(3):
        node=Node(False,["sample 2"],"subfolder"+str(i),-1)
        tree.insert(node)
        for j in range(3):
            node=Node(True,["sample 2","subfolder"+str(i)],"ssubsubfolder"+str(i)+str(j),-1)
            tree.insert(node)

    tree.print_graphml("test.graphml")
    tree.print_graphdot("test.graphdot")

