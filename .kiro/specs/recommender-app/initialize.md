We are in a repository for a new programming language and compiler. It is still unstable and barebones, but actively being developed. The goal is to create a web app entirely in this language, frontend backend everything. External components like Postgres etc can be used, but all source code we write should be written in Briev.

The app is a movie recommender system demo. It demonstrates the implementation of a collaborative filtering algorithm found in the PDF document found in this folder, and system design principles. The goal is to demonstrate that AI agents can easily write correct and performant software in this language.

The frontend should allow a visiting user to register an account (username + password). Minimal security is needed, as this is not a commercial app and if people lose their data or get hacked, that is acceptable. The username + password combo is just to separate users and allow them to store their system state.

The file u.data is used to bootstrap the recommender and give it a baseline to go off. A fresh user sees a list of movies and is asked to rate them. When they have rated at least 5, the system will start calculating predictions and serving them recommendations. It could work with a websocket connection, such that it is updating live as the user keeps rating more movies.

One central question is handling of the "rating matrix". As new users register and update ratings, some possibly precomputed values need to be updated. This probably can't be done for every user on every rating, rather there is a "cached" version that is served, and every now and then a new fresh one is calculated and replaces the stored one, or something like that.

We also want a simulator system, to use for simulating a large load on the system. It will create several users and connect them concurrently and update ratings so we can test how the system performs under pressure.

The Briev language is very barebones, and lacks many things like a fleshed out standard library and tooling. While we build this app we are building the necessary stdlib components and if necessary, fixing compiler bugs and language design gaps. Again, especially for the backend, no other programming languages such as Python or Node.js are allowed. Preferably the frontend will be written in Briev as well.

This will be a large project and I can't cover every single detail in this document, we will work details out as we go. From previous work we have WORKFLOW.md for instructions on how to navigate our development environment and an old tasks.md that can be used for reference. But for this project we probably should create a fresh spec, design and tasklist.