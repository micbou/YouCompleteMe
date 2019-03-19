#!/bin/bash

if [ -z $(git diff-index HEAD~1 README.md) ]; then
  echo "No changes to the README.md file."
  exit 0
fi

# Update Vim docs.
git clone https://github.com/micbou/vim-tools.git
pip install -r vim-tools/requirements.txt
python vim-tools/html2vimdoc.py -f youcompleteme README.md > doc/youcompleteme.txt
git add doc/youcompleteme.txt
git commit --author=${YCM_GITHUB_AUTHOR} --message="[skip ci] Update Vim documentation"
# Travis do a shallow clone by default. We need a full clone to push the commit.
git fetch --unshallow
git push https://${YCM_GITHUB_KEY}@github.com/${TRAVIS_REPO_SLUG} HEAD:master

# Update website.
git clone --branch=gh-pages https://github.com/${TRAVIS_REPO_SLUG} ycm-website
cd ycm-website
pip install -r requirements.txt
python update_from_readme.py ../README.md
git add index.html
git commit --author=${YCM_GITHUB_AUTHOR} --message="Update website"
git push https://${YCM_GITHUB_KEY}@github.com/${TRAVIS_REPO_SLUG}
