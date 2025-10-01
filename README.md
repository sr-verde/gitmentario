# Gitmentario

Gitmentario is a comment service for websites built with Static Site Generators (SSG).
Comments are pushed as markdown ressources into your website’s Git.


## Support

Gitmentario currently only supports [Hugo](https://gohugo.io) as SSG and Gitlab as software forge.
We plan to support at least Jekyll and Github, too.
At least Jekyll and Github are planned to be supported, too.


## Features

- Comments are true ressources of your website
- No vendor lock-in: You don’t loose your comments when moving to another approach
- Comment moderation
- Less JavaScript needed


## How It Works

1. A visitor writes a comment on your website as normal
2. A small JavaScript snippet sends this data to Gitmentario
3. Gitmentario creates a Markdown file from the comment
4. The tool either:
    - pushes the comment Markdown file directly to Git
    - creates a new branch, pushes the file into it, and opens a new MR


## Motivation

I run my personal website on WordPress for a long time.
When thinking about switching to Hugo, I always wanted to keep my (very few) comments users had made to my content.
So, I had the idea to somehow enable my website visitors to make a comment just as normal and push them to my website’s Git.
My search for a solution like that ended unsuccessful and my commitment of switching to Hugo abate.
A few years later, I came up with the idea again and found [Staticman](https://github.com/eduardoboucas/staticman) – that already existed for years!
But sadly, it isn’t maintained anymore and written in JS.
The latter detained me from taking over the maintenance.


## Built with Few Dependencies

Gitmentario is built using only a few but great open-source tools:

- [Fast API](https://fastapi.tiangolo.com/)
- [Pydantic and Pydantic Settings](https://pydantic.dev/)
- [python-gitlab](https://python-gitlab.readthedocs.io/)
- [PyYAML](https://pyyaml.org/)
