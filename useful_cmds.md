# useful_cmds

## Create a file with a list from most recent to oldest update to each branch
```
for branch in `git branch -r | grep -v HEAD`; do echo -e `git show --format="%ci %cr" $branch | head -n 1` \\t$branch; done | sort -r >> updated.txt
```

## Make remote repository mirror local (needed after removing remotes)
```
git push --mirror
```

## Use meld as diff tool
```
git config --global diff.tool meld
```

## Use meld for diffing branches
```
git difftool -d master..devel
```