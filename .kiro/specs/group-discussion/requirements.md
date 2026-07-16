# Group Discussion Requirements

## Introduction

Group Discussion (GD) ek naya feature hai jo real GD interviews ko simulate karta hai. 5-10 students ek room me join karke ek topic par free-flowing discussion karte hain using Push-to-Talk (PTT) mechanism. Har participant ka apna PTT button hota hai - press karne se local recording start, release karne par audio upload aur individually score hoti hai.

Multiple participants ek saath bol sakte hain (concurrent PTT) - real GDs ki tarah, short overlaps naturally hote hain but eventually one continues. Har person ka speak time, speech count, aur interruption count tracked hote hain, along with content quality (LLM-based).

## Requirements

### Requirement 1: GD Room Creation and Join
**User Story:** Student create/join GD room using 6-char code.

**Acceptance Criteria:**
1. WHEN user POSTs /gd/rooms, THE system SHALL create room with unique code, state=waiting
2. WHEN user joins with code and room.state=waiting AND count<10, THE system SHALL add them
3. IF room full (10 people) OR state != waiting, THEN reject with appropriate error
4. Minimum 5 participants required to start GD

### Requirement 2: Topic Assignment and Prep
**User Story:** Random topic assigned when room created, revealed at prep phase.

**Acceptance Criteria:**
1. WHEN room created, THE system SHALL pick random topic from gd_topics.json
2. Topic HIDDEN in waiting phase
3. WHEN all ready + count>=5, THE system SHALL enter prep phase (120s)
4. Prep phase REVEALS topic to all participants
5. WHEN prep timer expires, THE system SHALL transition to discussion phase

### Requirement 3: Push-to-Talk Speaking
**User Story:** Anyone can speak by holding Speak button; each speech recorded independently.

**Acceptance Criteria:**
1. WHILE room.state=discussion, THE system SHALL allow ANY participant to press Speak button
2. WHEN button pressed, THE frontend SHALL start LOCAL audio recording
3. WHEN button released, THE frontend SHALL upload audio blob to /gd/rooms/{code}/speech
4. Backend SHALL persist speech record with: speaker_id, start_time, end_time, audio_ref
5. Multiple concurrent speeches allowed - each recorded separately
6. Minimum speech duration: 2 seconds (shorter rejected)
7. Maximum single speech: 90 seconds (auto-stop)

### Requirement 4: Real-Time Speaking Indicators
**User Story:** All participants see who is currently speaking.

**Acceptance Criteria:**
1. WHEN participant presses Speak, THE system SHALL broadcast "user X started speaking"
2. WHEN participant releases Speak, THE system SHALL broadcast "user X stopped speaking"
3. UI SHALL show visual indicator for each speaking participant
4. Multiple speakers visible simultaneously

### Requirement 5: Discussion Duration and Auto-End
**User Story:** Discussion has time limit; ends automatically.

**Acceptance Criteria:**
1. Discussion phase duration: 15 minutes total
2. Countdown visible to all participants
3. WHEN timer expires OR host clicks End, THE system SHALL transition to scoring phase
4. Last 30 seconds warning displayed

### Requirement 6: Scoring System
**User Story:** Each participant gets individual score after GD ends.

**Acceptance Criteria:**
Score breakdown (100 points):
1. Content Quality (30%): LLM-based analysis of all speeches
2. Communication (20%): Pronunciation + Fluency avg across speeches
3. Participation (20%): Total speak time + number of contributions
4. Listening (15%): References to other participants' points
5. Leadership (15%): First speaker, guiding discussion (heuristic)

### Requirement 7: Post-Discussion Analysis
**User Story:** Results shown after batch processing.

**Acceptance Criteria:**
1. WHEN discussion ends, THE system SHALL enter scoring state
2. Backend batch processes ALL speeches (audio → transcript → scores)
3. LLM analyzes overall content quality per participant
4. Total processing time: 30-60 seconds
5. Results include: individual scores, rankings, feedback per participant

### Requirement 8: Concurrent Speech Handling
**User Story:** Handle multiple simultaneous speakers gracefully.

**Acceptance Criteria:**
1. System SHALL track overlap: if speech A starts while B is speaking → mark as "interruption"
2. Interruption count SHALL affect leadership/etiquette score
3. All concurrent speeches SHALL be scored independently
4. No speech is dropped or ignored

### Requirement 9: WebSocket State Broadcast
**User Story:** Real-time state sync across all participants.

**Acceptance Criteria:**
1. WebSocket at /gd/ws/{code} with Firebase auth
2. Broadcast on: join, ready, phase transitions, speak start/stop, timer updates
3. Speaking indicators updated in real-time (< 500ms latency)

### Requirement 10: Non-Modification Boundaries
1. SHALL NOT modify existing /app/pronunciation/, /app/asr/, /app/audio/, /app/debate/
2. SHALL reuse existing ASR + pronunciation pipeline for speech analysis
3. New module: /app/gd/ (fully isolated)
4. Frontend: additive changes only

## Glossary
- **GD_Session**: Backend entity for one group discussion instance
- **Speech**: One individual audio recording from press to release
- **Participant**: Authenticated user in GD room
- **Interruption**: Speech started while another speech was ongoing
- **PTT**: Push-to-Talk mechanism
