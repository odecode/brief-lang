# Requirements Document

## Introduction

This spec defines a movie-recommender web application written **entirely in
Briev** — frontend and backend both. External infrastructure (a PostgreSQL
database) is permitted, but every line of application source code is Briev. The
project is a demonstration that AI agents can author correct and performant
software in the Briev language, and a forcing function that grows the Briev
standard library (particularly the network stack) as the build surfaces the
pieces it needs.

The application lets a visitor register an account, rate movies, and receive
personalized recommendations produced by a neighborhood collaborative filtering
(CF) algorithm. The algorithm implements the full **Auto-Adaptive Imputation
Fusion (AutAI-Fusion)** predictor from the source paper, "The Efficient
Imputation Method for Neighborhood-based Collaborative Filtering" (Ren, Li,
Zhang, Zhou; CIKM'12): it computes BOTH the user-based predictor (paper Eq. 29)
and the item-based predictor (paper Eq. 30) and blends them by the fusion weight
λ (paper Eq. 31). Correctness is defined as **faithfulness to the paper's
AutAI-Fusion algorithm** — the true per-user mean and true per-item mean,
Pearson-correlation similarity over the respective imputed key-set spaces (user-
user Eq. 9 and item-item Eq. 10), actual (executed) key-neighborhood imputation
on both sides, each neighbor used exactly once with proper η normalization, and
the λ-weighted fusion of the two predictions. The user-user and item-item
similarity matrices and the per-user and per-item means are **computed from the
current rating population derived from u.data**, per Eqs. 9 and 10. The bundled
C++ implementation (`recommender_singlepass.cpp`) is **only a performance
baseline**, not the behavioral reference: its observed quirks (a per-user mean
degenerating to 1.0, a dead imputation loop that never runs, and an off-by-one
neighbor walk that counts the first neighbor twice and drops the last) are
**defects the Briev implementation SHALL NOT reproduce**. The MovieLens-100k
dataset (`u.data`) bootstraps the system with a baseline. The precomputed
similarity artifact (`simlist.txt` / `simlist.txt.bin`) is NO LONGER treated as
authoritative ground truth; it serves as a cache artifact and/or a validation
fixture for the computed similarity data.

Recommendations update live over a websocket as the user rates more movies.
Because recomputing similarity per-user-per-rating is prohibitively expensive, a
cached similarity artifact is served and periodically (or on trigger) refreshed
and swapped in. A load-simulator subsystem creates many concurrent users and
streams ratings to stress-test the system.

Security is intentionally minimal: this is a non-commercial demo, and data loss
or breach is acceptable. Usernames and passwords exist only to separate users
and persist their state.

Several network-stack standard-library components this app depends on **do not
yet exist** and are in-scope work surfaced by this build. They are called out
explicitly in Requirement 9 and flagged inline where relevant. The requirements
below describe **what** the system must do and **why**; the **how**
(architecture, module layout, data structures, wire protocols) is deferred to
the design phase.

## Glossary

- **Recommender_System**: The complete application comprising the Briev backend,
  the Briev frontend, the CF engine, the websocket layer, and the simulator.
- **Backend**: The server-side Briev program handling HTTP/websocket requests,
  database access, and recommendation serving.
- **Frontend**: The client-side Briev program a visitor interacts with in a
  browser (registration, rating, recommendation display).
- **CF_Engine**: The collaborative-filtering computation that produces
  predicted ratings for a user, implementing the paper's full AutAI-Fusion
  predictor (user-based Eq. 29 and item-based Eq. 30, blended by λ per Eq. 31).
- **Reference_Algorithm**: The full Auto-Adaptive Imputation Fusion (AutAI-
  Fusion) method defined in "The Efficient Imputation Method for Neighborhood-
  based Collaborative Filtering" (Ren, Li, Zhang, Zhou; CIKM'12). This is the
  authoritative specification of the CF_Engine's correct behavior and comprises
  both predictors: the user-based predictor (true per-user mean ūa, user-user
  PCC similarity over the imputed key-set space per Eq. 9, user key-neighborhood
  imputation per Eq. 7, and prediction per Eq. 29) and the item-based predictor
  (true per-item mean t̄s, item-item PCC similarity over the imputed item key-set
  per Eq. 10, item key-neighborhood imputation per Section 3.2 / N'a,s, and
  prediction per Eq. 30), fused by the weight λ per Eq. 31.
- **Performance_Baseline**: `recommender_singlepass.cpp`, the bundled C++
  implementation. It is used ONLY as a speed reference for performance
  comparison. Its observable behavior is NOT a correctness target; its known
  defects (per-user mean degenerating to 1.0, a dead imputation loop, and an
  off-by-one neighbor walk) SHALL NOT be reproduced.
- **Account_Service**: The backend component handling registration and login.
- **Rating_Store**: The persistence layer (PostgreSQL via a Briev client) that
  holds accounts, ratings, and user state.
- **Similarity_Matrix**: The similarity data computed by the CF_Engine from the
  current rating population, comprising BOTH the user-user PCC matrix (943 × 943,
  per Eq. 9) and the item-item PCC matrix (1682 × 1682, per Eq. 10). The
  `simlist.txt` / `simlist.txt.bin` artifact is a cache/validation fixture for
  this computed data, not an external source of truth.
- **Similarity_Cache**: The served snapshot of the computed Similarity_Matrix
  (both the user-user and item-item PCC matrices) that the CF_Engine reads,
  refreshed periodically or on trigger rather than per rating. `simlist.txt.bin`
  is a persisted form of this cache and/or a comparison fixture, not an external
  source of truth.
- **Cold_Start_Flow**: The experience for a fresh user who must rate movies
  before the system can serve them recommendations.
- **Rating_Threshold**: The minimum number of ratings a user must submit before
  the system begins serving them recommendations. Its value is 5.
- **Live_Channel**: The websocket connection carrying live recommendation
  updates from Backend to Frontend.
- **Load_Simulator**: The subsystem that creates many users, connects them
  concurrently, and streams ratings to exercise the system under load.
- **Net_Stack**: The Briev standard-library networking modules under
  `lib/std/net/` and `lib/std/db/` the Backend is built on.
- **u.data**: The MovieLens-100k ratings file (1-indexed `user item rating
  timestamp` records) used to bootstrap the baseline. 943 users, 1682 items.
- **Prediction**: A predicted rating value for a (user, item) pair, equal to the
  Fusion_Prediction (the λ-blended combination of the user-based and item-based
  predictions), clamped to the valid MovieLens rating scale, the range 1 through
  5 inclusive.
- **User_Mean**: The true arithmetic average of a user's observed (non-missing)
  ratings, denoted ūa in the Reference_Algorithm.
- **Item_Mean**: The true arithmetic average of a given item's observed (non-
  missing) ratings, denoted t̄s in the Reference_Algorithm.
- **Lambda**: The fusion weight λ ∈ [0,1] that blends the user-based and item-
  based predictions per Eq. 31 (λ = 1 ⇒ pure user-based, λ = 0 ⇒ pure item-
  based). Its exact value is a design-tunable set in the design phase or by
  cross-validation, with a neutral default of 0.5.
- **Fusion_Prediction**: The λ-blended prediction r̂as = λ · r̂ᵘas + (1 − λ) ·
  r̂ⁱas (paper Eq. 31), combining the user-based prediction r̂ᵘas (Eq. 29) and
  the item-based prediction r̂ⁱas (Eq. 30). This is the served Prediction value.
- **Key_Neighborhood**: The active user's user-based key neighborhood Na,s whose
  missing values are imputed per the Reference_Algorithm (paper Eq. 7), and the
  active item's item-based key neighborhood N'a,s whose missing values are
  imputed per the Reference_Algorithm (paper Section 3.2), each imputed before
  its respective prediction.
- **Neighbor_Count**: The number of nearest neighbors k used in prediction. Its
  default is 30, the Reference_Algorithm's setting; the exact value is a
  design-tunable.
- **Top_N**: The number of items returned in a Recommendation_Set. Its default
  is 5.
- **Recommendation_Set**: The top-N (default 5) predicted items served to a
  user, ordered by predicted rating descending with a deterministic tie order,
  excluding items the user has already rated.

## Requirements

### Requirement 1: Account Registration and Login

**User Story:** As a visitor, I want to register an account with a username and
password and log back into it, so that the system can separate my data from
other users and persist my ratings and recommendations across sessions.

#### Acceptance Criteria

1. WHEN a visitor submits a registration request with a username that is not
   already registered and a non-empty password, THE Account_Service SHALL create
   a new account associated with that username and persist it to the
   Rating_Store.
2. IF a visitor submits a registration request with a username that is already
   registered, THEN THE Account_Service SHALL reject the request and return an
   account-exists error.
3. IF a visitor submits a registration request with an empty username or an
   empty password, THEN THE Account_Service SHALL reject the request and return
   a validation error.
4. WHEN a visitor submits a login request with a username and a password that
   match a persisted account, THE Account_Service SHALL establish an
   authenticated session for that account.
5. IF a visitor submits a login request whose username is not registered or
   whose password does not match the persisted account, THEN THE
   Account_Service SHALL reject the request and return an authentication-failed
   error.
6. WHEN an authenticated account's state is requested, THE Backend SHALL return
   that account's own ratings and recommendations and no other account's data.

### Requirement 2: Baseline Bootstrap from u.data

**User Story:** As an operator, I want the system to load the MovieLens-100k
baseline from u.data on startup, so that the recommender has a population of
existing ratings to compute neighborhoods from before any new user registers.

#### Acceptance Criteria

1. WHEN the Backend starts and the Rating_Store does not already contain the
   baseline, THE Backend SHALL parse `u.data` and load every valid `user item
   rating timestamp` record into the Rating_Store.
2. WHEN the Backend parses a `u.data` record whose 1-indexed user is in the
   range 1 through 943 and whose 1-indexed item is in the range 1 through 1682,
   THE Backend SHALL store that record as a rating for the corresponding
   0-indexed user and item.
3. IF a `u.data` record references a user outside 1 through 943 or an item
   outside 1 through 1682, THEN THE Backend SHALL discard that record and
   continue loading the remaining records.
4. WHEN the baseline load completes, THE Backend SHALL expose the 943 baseline
   users and their ratings to the CF_Engine as the starting rating population.
5. WHEN the Backend starts and the Rating_Store already contains the baseline,
   THE Backend SHALL skip re-loading `u.data` and use the persisted baseline.

### Requirement 3: Cold-Start Rating Flow

**User Story:** As a fresh user, I want to be shown movies to rate when I have
too little history, so that the system can gather enough of my preferences to
start recommending movies to me.

#### Acceptance Criteria

1. WHILE an authenticated user has submitted fewer than 5 ratings, THE Frontend
   SHALL present the user with movies to rate and SHALL NOT present a
   Recommendation_Set.
2. WHEN an authenticated user submits a rating for a movie, THE Backend SHALL
   persist that rating to the Rating_Store associated with the user's account.
3. WHEN an authenticated user has submitted at least 5 ratings, THE Backend
   SHALL begin computing predictions for that user and serving them a
   Recommendation_Set.
4. IF a user submits a rating value outside the range 1 through 5, THEN THE
   Backend SHALL reject the rating and return a validation error.
5. WHEN a user submits a rating for a movie the user has already rated, THE
   Backend SHALL replace the user's prior rating for that movie with the new
   value.

### Requirement 4: Serving Recommendations (Paper-Faithful AutAI-Fusion CF)

**User Story:** As a user with enough rating history, I want to receive movie
recommendations computed by a correct collaborative-filtering engine faithful to
the full AutAI-Fusion paper (user-based and item-based predictors blended by λ),
so that I discover movies I am predicted to rate highly.

#### Corrected Behavior (Non-Goals)

The Performance_Baseline (`recommender_singlepass.cpp`) exhibits three defects
that the CF_Engine SHALL NOT reproduce: a per-user mean that degenerates to 1.0,
an imputation loop that is dead code and never executes, and an off-by-one
neighbor walk that counts the first rating neighbor twice and drops the last.
The acceptance criteria below encode the paper-faithful behavior that replaces
each defect. These corrections apply to BOTH predictors: the user-based side
(true User_Mean, executed user imputation, no off-by-one user-neighbor walk) and
the item-based side (true Item_Mean rather than a degenerate constant, executed
item imputation rather than dead code, and an item-neighbor walk with no off-by-
one). Correctness is measured against the Reference_Algorithm, not against the
Performance_Baseline's observable output.

#### Acceptance Criteria

**User-based predictor (paper Eqs. 7, 9, 29):**

1. WHEN the CF_Engine computes a User_Mean for a user who has rated at least one
   item, THE CF_Engine SHALL use the true arithmetic average of that user's
   observed ratings and SHALL NOT substitute a degenerate constant mean.
2. WHEN the CF_Engine computes the similarity between two users, THE CF_Engine
   SHALL compute the Pearson Correlation Coefficient over the imputed user key-
   set item space using mean-centered ratings, as specified by the
   Reference_Algorithm (paper Eq. 9).
3. WHEN the CF_Engine prepares to compute the user-based prediction for an
   active user, THE CF_Engine SHALL impute the missing values in that user's
   user-based Key_Neighborhood per the Reference_Algorithm (paper Eq. 7, r̂a'i =
   ūa' plus the weighted neighbor deviations) and SHALL execute the imputation
   rather than skipping it.
4. WHEN the CF_Engine computes the user-based prediction r̂ᵘas for a (user, item)
   pair, THE CF_Engine SHALL compute r̂ᵘas = ūa + ( Σ over ux in the k nearest
   user-neighbors who rated the item of sim'(ua,ux) · (rxs − ūx) ) / ( Σ over ux
   in the k nearest user-neighbors who rated the item of sim'(ua,ux) ), as
   specified by the Reference_Algorithm (paper Eq. 29, user-based AutAI).

**Item-based predictor (paper Eqs. 10, 30, Section 3.2):**

5. WHEN the CF_Engine computes an Item_Mean for an item that has at least one
   observed rating, THE CF_Engine SHALL use the true arithmetic average of that
   item's observed ratings and SHALL NOT substitute a degenerate constant mean.
6. WHEN the CF_Engine computes the similarity between two items, THE CF_Engine
   SHALL compute the Pearson Correlation Coefficient over the imputed item key-
   set user space using mean-centered ratings, as specified by the
   Reference_Algorithm (paper Eq. 10).
7. WHEN the CF_Engine prepares to compute the item-based prediction for an
   active item, THE CF_Engine SHALL impute the missing values in that item's
   item-based Key_Neighborhood (N'a,s) per the Reference_Algorithm (paper
   Section 3.2) and SHALL execute the imputation rather than skipping it.
8. WHEN the CF_Engine computes the item-based prediction r̂ⁱas for a (user, item)
   pair, THE CF_Engine SHALL compute r̂ⁱas = t̄s + ( Σ over ti in the k nearest
   item-neighbors of ts that the active user rated of sim'(ts,ti) · (rai − t̄i) )
   / ( Σ over ti in the k nearest item-neighbors of ts that the active user
   rated of sim'(ts,ti) ), as specified by the Reference_Algorithm (paper Eq.
   30, item-based AutAI).

**Shared neighbor-aggregation rules (apply to both predictors):**

9. WHEN the CF_Engine aggregates neighbor contributions for either the user-
   based or the item-based prediction, THE CF_Engine SHALL use each qualifying
   neighbor exactly once, SHALL NOT count the first neighbor twice, and SHALL NOT
   drop the last neighbor.
10. WHEN the CF_Engine normalizes the user-based prediction, THE CF_Engine SHALL
    divide the weighted user-neighbor-deviation sum by the normalizing factor η
    equal to the sum of sim'(ua,ux) over the same k nearest user-neighbors used
    in the numerator.
11. WHEN the CF_Engine normalizes the item-based prediction, THE CF_Engine SHALL
    divide the weighted item-neighbor-deviation sum by the normalizing factor η
    equal to the sum of sim'(ts,ti) over the same k nearest item-neighbors used
    in the numerator.
12. WHEN the CF_Engine selects the k nearest neighbors for either predictor, THE
    CF_Engine SHALL use a Neighbor_Count defaulting to 30, the
    Reference_Algorithm's setting.

**Fusion and serving (paper Eq. 31):**

13. WHEN the CF_Engine produces a Fusion_Prediction for a (user, item) pair, THE
    CF_Engine SHALL compute r̂as = λ · r̂ᵘas + (1 − λ) · r̂ⁱas as specified by the
    Reference_Algorithm (paper Eq. 31), using a Lambda value in the range 0
    through 1 inclusive that defaults to 0.5 and whose exact value is set in the
    design phase or by cross-validation.
14. WHEN the CF_Engine produces a Prediction, THE CF_Engine SHALL clamp the
    fused Fusion_Prediction value to the valid MovieLens rating scale, the range
    1 through 5 inclusive.
15. IF the user-based normalizing factor η is zero because no qualifying user-
    neighbor rated the item, THEN THE CF_Engine SHALL substitute the active
    user's true User_Mean for the user-based prediction r̂ᵘas before fusion.
16. IF the item-based normalizing factor η is zero because no qualifying item-
    neighbor of the item was rated by the active user, THEN THE CF_Engine SHALL
    substitute the active item's true Item_Mean for the item-based prediction
    r̂ⁱas before fusion.
17. IF both normalizing factors η are zero so that neither predictor has a
    qualifying neighbor, THEN THE CF_Engine SHALL produce the fused combination
    of the active user's true User_Mean and the active item's true Item_Mean per
    Eq. 31, clamped to the range 1 through 5.
18. WHEN the CF_Engine serves a Recommendation_Set for a user, THE CF_Engine
    SHALL exclude every item the user has already rated.
19. WHEN the CF_Engine serves a Recommendation_Set for a user, THE CF_Engine
    SHALL return the Top_N (default 5) highest-predicted items ordered by fused
    predicted rating descending, breaking ties by item index ascending as the
    CF_Engine's own deterministic order.
20. WHEN the CF_Engine reads similarity data for a prediction, THE CF_Engine
    SHALL compute the user-user and item-item PCC similarity matrices from the
    current rating population per the Reference_Algorithm (paper Eqs. 9 and 10)
    and SHALL NOT treat the `simlist.txt` / `simlist.txt.bin` artifact as
    authoritative ground truth.

### Requirement 5: Live Recommendation Updates

**User Story:** As a user actively rating movies, I want my recommendations to
update live without reloading the page, so that I immediately see the effect of
each new rating.

#### Acceptance Criteria

1. WHEN an authenticated user opens the rating experience, THE Frontend SHALL
   establish a Live_Channel to the Backend.
2. WHEN an authenticated user submits a rating over an open Live_Channel and the
   user has at least 5 ratings, THE Backend SHALL send an updated
   Recommendation_Set over that Live_Channel.
3. WHILE a Live_Channel is open, THE Frontend SHALL display the most recently
   received Recommendation_Set.
4. IF a Live_Channel closes unexpectedly, THEN THE Frontend SHALL attempt to
   re-establish the Live_Channel.
5. WHEN the Backend sends a Recommendation_Set over a Live_Channel, THE Backend
   SHALL send it only to the Live_Channel belonging to the account that owns the
   ratings.

> **Net-stack dependency:** The Live_Channel requires a websocket module that
> does not yet exist in the Net_Stack (see Requirement 9).

### Requirement 6: Similarity Caching and Periodic Refresh

**User Story:** As an operator, I want the system to serve a cached snapshot of
the computed similarity matrices and refresh it periodically rather than
recomputing it on every rating, so that recommendation serving stays fast as
users and ratings grow.

#### Acceptance Criteria

1. WHEN the Backend starts, THE Backend SHALL load the Similarity_Cache (the
   computed user-user and item-item PCC matrices) from the persisted binary
   artifact (`simlist.txt.bin`) when that artifact is fresh.
2. IF the persisted binary artifact is absent or stale relative to the current
   rating population, THEN THE Backend SHALL compute the Similarity_Cache (both
   the user-user and item-item PCC matrices) from the rating population per Eqs.
   9 and 10 and write a refreshed binary artifact.
3. WHILE serving recommendations, THE CF_Engine SHALL read user-user and item-
   item similarity values from the currently served Similarity_Cache rather than
   recomputing them per request.
4. WHEN a refresh is triggered, either on a periodic schedule or on an explicit
   trigger, THE Backend SHALL recompute a new Similarity_Cache (both matrices)
   from the current rating population per Eqs. 9 and 10 and swap it in as the
   served snapshot.
5. WHILE a Similarity_Cache refresh is in progress, THE CF_Engine SHALL continue
   serving recommendations from the previously served snapshot until the new
   snapshot is swapped in.
6. WHEN the Backend validates whether the persisted binary artifact is fresh,
   THE Backend SHALL compare the artifact's recorded rating-population signature
   (record count and modification time of the backing rating source) against the
   current rating population and treat a mismatch as stale.
7. WHERE the shipped `simlist.txt` artifact is present, THE Backend SHALL treat
   it as a validation fixture for comparison against the computed similarity
   matrices and SHALL NOT treat it as the authoritative source of the served
   Similarity_Cache.

### Requirement 7: Load Simulation Subsystem

**User Story:** As an operator, I want a simulator that creates many users and
streams ratings concurrently, so that I can measure how the system behaves under
load.

#### Acceptance Criteria

1. WHEN the Load_Simulator is started with a requested user count, THE
   Load_Simulator SHALL register that many accounts against the Backend.
2. WHEN the Load_Simulator has registered its accounts, THE Load_Simulator SHALL
   open a concurrent Live_Channel for each simulated user.
3. WHILE the Load_Simulator is running, THE Load_Simulator SHALL stream rating
   submissions from its simulated users to the Backend.
4. WHEN the Load_Simulator completes a run, THE Load_Simulator SHALL report the
   number of ratings submitted and the number of Recommendation_Sets received.
5. IF a simulated user's Live_Channel fails during a run, THEN THE
   Load_Simulator SHALL record the failure and continue the run with the
   remaining simulated users.

### Requirement 8: Pure-Briev Implementation Constraint

**User Story:** As the project owner, I want all application source written in
Briev over the Briev net stack, so that the project demonstrates Briev's ability
to build a complete, correct, performant system end to end.

#### Acceptance Criteria

1. THE Recommender_System SHALL implement all Backend application logic in Briev
   source compiled by the Briev compiler.
2. THE Backend SHALL communicate with external infrastructure (PostgreSQL) only
   through a client written in Briev over the Net_Stack, with no third-party
   language runtime (Python, Node.js) or non-Briev database library in the
   application path.
3. THE Frontend SHALL be implemented in Briev source.
4. WHEN the Backend requires a networking capability (TCP sockets, PostgreSQL
   wire protocol, HTTP, websocket, HTTP fetch), THE Recommender_System SHALL
   provide that capability as a Net_Stack standard-library module written in
   Briev.
5. WHERE the interpreter executes a program correctly, THE Briev backend SHALL
   compile that program to equivalent observable behavior, treating the
   interpreter as the reference per the repository operating contract.

### Requirement 9: Net-Stack Standard-Library Dependencies

**User Story:** As a Briev stdlib maintainer, I want the net-stack components the
app depends on identified as in-scope deliverables, so that the missing pieces
are built as first-class standard-library modules rather than worked around.

#### Acceptance Criteria

1. THE Net_Stack SHALL provide a byte-buffer module (`lib/std/net/bytes.bv`) for
   wire-protocol byte framing. (Status: already implemented.)
2. THE Net_Stack SHALL provide a TCP socket module (`lib/std/net/socket.bv`)
   offering connect, send, receive, listen, and accept over raw system calls.
   (Status: not yet implemented.)
3. THE Net_Stack SHALL provide a PostgreSQL wire-protocol client module
   (`lib/std/db/pg.bv`) offering connection, authentication, simple queries, and
   parameterized queries. (Status: not yet implemented.)
4. THE Net_Stack SHALL provide an HTTP/1.1 server module (`lib/std/net/http.bv`)
   for request parsing and response writing. (Status: not yet implemented.)
5. THE Net_Stack SHALL provide a websocket module for the Live_Channel upgrade
   handshake and frame encoding/decoding. (Status: not yet implemented.)
6. THE Net_Stack SHALL provide a frontend HTTP fetch module
   (`lib/std/web/fetch.bv`) for the Frontend to call the Backend API. (Status:
   not yet implemented.)
7. WHEN building any Net_Stack module surfaces a Briev compiler bug or a language
   gap, THE project SHALL record the bug and its root cause rather than working
   around it in the standard library, per the repository operating contract.

### Requirement 10: Performance and Responsiveness

**User Story:** As the project owner, I want recommendation serving to be
competitive with the reference C++ implementation and the system to stay
responsive under simulated load, so that the demo shows Briev produces software
that is performant, not merely correct.

#### Acceptance Criteria

1. WHEN the CF_Engine serves a Recommendation_Set for a user against the
   bootstrap population, THE CF_Engine SHALL complete the prediction phase within
   a bounded multiple of the Performance_Baseline's prediction time on the same
   dataset, with the acceptable multiple fixed in the design phase accounting for
   the additional work of the AutAI-Fusion engine (two similarity matrices, two
   predictors, and the λ fusion). This bound compares runtime only and does not
   imply behavioral equivalence to the Performance_Baseline, whose correctness
   defects the CF_Engine does not reproduce (see Requirement 4).
2. WHEN an authenticated user submits a rating over a Live_Channel, THE Backend
   SHALL send the updated Recommendation_Set within a bounded latency fixed in
   the design phase.
3. WHILE the Load_Simulator streams ratings from its simulated users, THE
   Backend SHALL continue to accept new rating submissions and serve
   Recommendation_Sets without rejecting valid requests due to resource
   exhaustion up to a concurrency bound fixed in the design phase.
4. WHEN serving recommendations under load, THE CF_Engine SHALL read from the
   Similarity_Cache rather than recomputing similarity, so that per-request cost
   does not scale with the rating population size.

## Approved responsiveness contract (2026-10-22)

The authoritative v1 interface freeze is
[recommender responsiveness contract](../../../docs/architecture/applications/recommender-responsiveness-contract-v1.md).
It supersedes synchronous write/recompute consistency and unmeasured latency
claims below. Acceptance updates the account-owned in-memory profile; prediction
and durable persistence run independently. Saved means committed, pending does
not. The shared immutable population model may lag commits while predictions use
the current accepted profile and exclude its old population row. Save completion
never starts prediction or changes recommendation contents. Exact paper-faithful
math remains required. Epoch/revision/job tags, durable idempotent receipts,
bounded reservations, FIFO retry/discard and session lifetime follow v1.

I02 supplies tested pure types/codecs/policies, not the asynchronous production
cutover. I03–I17 implement and verify that cutover. Warm responsiveness targets
are acceptance goals for I16, not established measurements; I01 records the
actual slow baseline, timeouts and resource growth.
