__author__ = 'lars'

from functools import reduce
from collections import Counter
from hashlib import md5
import os
class Tree:
    def __init__(self,root):
        """

        :rtype : Tree
        """
        self.root=root

    def search(self,path):
        return self.root.dfs_path(path)

    def insert(self,node):
        self.root.dfs_insert(node)

    def create_checksums(self):
        self.root.dfs_create_checksums()

    def generate_checksum_list(self):
        return self.root.dfs_generate_checksum_list([])

    def treeshake(self):
        print("_--------------")
        print(os.listdir("./sample/"))
        if self.root.dfs_treeshake():
            print("treeshake finished, there are potential dups")
            return
        else:
            print("the tree doesn't contain any duplicates")

    def find_duplicates(self,filename):
        self.treeshake()
        self.create_checksums()
        checksum_list=self.generate_checksum_list()
        duplicate_checksums=[x for x, y in Counter(checksum_list).items() if y > 1]
        duplicates={}
        if duplicate_checksums:
            print("there are folders or files with the same checksum")
            print(duplicate_checksums)
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
            file=open(filename,"w")
            print("""digraph filesystem {""",file=file)
            self.root.dfs_print_graphdot(file)
            print("""}""",file=file)
            file.flush()
            file.close()



class Node:
    def __init__(self, isFile,path, name, id):
        """

        :rtype : Node
        """
        self.isFile=isFile
        self.path=path
        self.name=name
        self.id=id
        self.children=[]
        self.parent=None
        self.checksum=None

    def addChild(self,child):
        self.children.append(child)

    def setParent(self,parent):
        if(parent!=None):
            print("overwriting parent")
        self.parent=parent

    def isDuplicate(self):
        if self.isFile:
            return True
        elif self.children==[]:
            return False
        else:
            return reduce(lambda x,y: x.isDuplicate() and y.isDuplicate, self.children)

    def dfs_insert(self,node):

        # we need to insert the node in the tree
        # first: search how much of the folder structure is already there
        """

        :type node: None
        """
        node_path=node.path.copy()
        current_node=self.dfs_search_for_partial_path(node_path)

        # get the path that was found
        partial_path=current_node.path.copy()
        partial_path.append(current_node.name)

        # this path has to be created by hand
        path_rest=node_path[len(partial_path):len(node_path)]

        current_path=partial_path

        for elem in path_rest:
            temp_node=Node(False,current_path,elem,-1)
            current_node.children.append(temp_node)
            current_node=temp_node
            current_path=current_path+[elem]

        current_node.children.append(node)

    def dfs_search_for_checksum(self,checksum,dups_list):
        if self.checksum.digest()==checksum:
            dups_list.append(self)
        for child in self.children:
            dups_list=child.dfs_search_for_checksum(checksum,dups_list)
        return dups_list

    def dfs_search_for_path(self,path):
        if self.name!=path[0]:
            raise Exception("the dfs has led to a problem")
        elif len(path)>1:
            folder=path[1]
            for child in self.children:
                if folder==child.name:
                    return child.dfs_search_for_path(path(1,len(path)))
            raise Exception("the path does not exist in the tree")
        else:
            return self

    def dfs_search_for_partial_path(self,path):
        if self.name!=path[0]:
            raise Exception("the dfs has led to a problem")
        elif len(path)>1:
            folder=path[1]
            for child in self.children:
                if folder==child.name:
                    return child.dfs_search_for_path(path[1:len(path)])
            return self
        else:
            return self

    def dfs_create_checksums(self):
        if self.children==[]:
            self.checksum=md5()
            self.checksum.update(str(self.id).encode("utf-8"))
            return

        else:
            children_checksums=[]
            for child in self.children:
                child.dfs_create_checksums()
                children_checksums.append(child.checksum.digest())

            children_checksums.sort()
            self.checksum=md5()
            for child_checksum in children_checksums:
                self.checksum.update(child_checksum)
            return

    def dfs_print_graphml(self,file):
        print("<node id=\""+self.name+"\" />",file=file)
        for child in self.children:
            child.dfs_print_graphml(file)
            print("<edge source=\""+self.name+"\" target=\""+child.name+"\"/>",file=file)

    def dfs_print_graphdot(self,file):
        for child in self.children:
            print(("".join(self.path)+self.name).replace("/","_").replace("\n","")+"->"+("".join(child.path)+child.name).replace("/","_").replace("\n","")+";",file=file)
            child.dfs_print_graphdot(file)

    def dfs_treeshake(self):
        """
        Check if this could potentially be a duplicate.
        Return True if yes, False otherwise
        """
        if self.isFile:
            return True

        num_files=os.listdir("./"+"/".join(self.path)+"/"+self.name+"")
        children_to_be_removed=[]
        for child in self.children:
            if not child.dfs_treeshake():
                children_to_be_removed.append(child)

        if len(num_files)>len(self.children):
            return False
        for child in children_to_be_removed:
            self.children.remove(child)

        if not self.children:
            return self.isFile

        return True

    def dfs_generate_checksum_list(self,checksum_list):
        for child in self.children:
            child.dfs_generate_checksum_list(checksum_list)
        checksum_list.append(self.checksum.digest())
        return checksum_list



if __name__=="__main__":
    print("testing the tree")
    root=Node(False,[],"/sample",-1)
    tree=Tree(root)
    for i in range(3):
        node=Node(False,["/sample"],"/subfolder"+str(i),-1)
        tree.insert(node)
        for j in range(3):
            node=Node(True,["/sample","/subfolder"+str(i)],"/subsubfolder"+str(i)+str(j),-1)
            tree.insert(node)

    tree.print_graphml("test.graphml")
    tree.print_graphdot("test.graphdot")
    tree.treeshake()
    tree.create_checksums()
    checksum_list=tree.generate_checksum_list()
    print(len(checksum_list))
    print("these checksums appear more than once")
    print([x for x, y in collections.Counter(checksum_list).items() if y > 1])

    print("these folder/files have identical checksums")
    dups=tree.find_duplicates("dups_found.txt")
    print(dups)

    for key in dups:
        print("a set of dups")
        for value in dups[key]:
            print("".join(value.path)+value.name)

        print("-----------------------")
