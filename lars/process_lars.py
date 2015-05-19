__author__ = 'lars'

from lars.Tree import Tree
from lars.Tree import Node
from subprocess import call
import os

if __name__=="__main__":

    print(os.listdir("."))
    call("fdupes -r sample/ > out.txt",shell=True)
    
    with open("out.txt") as file:
        duplicates={}
        id=0
        root=Node(False,[],"sample",-1)
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
            if not (path_string in duplicates):
                duplicates[path_string]=[]

            duplicates[path_string].append(name)

            new_node=Node(True,path,name,id)
            tree.insert(new_node)

        print(duplicates)

        duplicate_paths=[]
        for key in duplicates:
            value=duplicates[key]
            if len(value)>1:
                duplicate_paths.append(key)

        print(duplicate_paths)
        tree.print_graphdot("test.graphdot")
        tree.find_duplicates("dups_found.txt")