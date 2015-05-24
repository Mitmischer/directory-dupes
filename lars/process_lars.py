__author__ = 'lars'

from Tree import Tree
from Tree import Node
from subprocess import call
import os

if __name__=="__main__":

    print(os.listdir("."))
    target=input("please enter a filename to be scanned for duplicates:")
    print("target:" + target)
    call("fdupes -r \""+target+"\" > fdupes_output.txt",shell=True)

    with open("fdupes_output.txt") as file:
        id=0
        root=Node(False,[],target,-1)
        tree=Tree(root)
        
        for line in file:
            # strip off the trailing newline
            line=line[0:-1]
            if line=="":
                print("empty line")
                id+=1
                continue
            print(line,id)

            # split the line into path and filename
            parts=line.split("/")
            path=parts[0:-1]
            path_string="/".join(path)
            name=parts[-1]
            new_node=Node(True,path,name,id)
            tree.insert(new_node)

        tree.print_graphdot("test.graphdot")
        tree.find_toplevel_duplicates("dups_found.txt")