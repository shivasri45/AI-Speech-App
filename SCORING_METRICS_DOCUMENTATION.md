# KIET Soft Skills Platform - Scoring Metrics Documentation

**Comprehensive guide to all AI scoring algorithms used across features**

---

## Table of Contents
1. [Pronunciation Practice](#1-pronunciation-practice)
2. [1v1 Battle](#2-1v1-battle)
3. [Group Debate](#3-group-debate)
4. [Interview Studio (Gesture & Posture)](#4-interview-studio-gesture--posture)
5. [Voice CruiseControl](#5-voice-cruisecontrol)

---

## 1. Pronunciation Practice

### Overview
Analyzes uploaded audio against expected text to evaluate pronunciation accuracy, fluency, and clarity.

### Metrics & Algorithms

#### A. **Pronunciation Score** (0-100)
**Algorithm:** Phoneme-level acoustic analysis using HuggingFace Wav2Vec2

**Process:**
1. **Expected Phonemes Generation:**
   - Input text → CMU Pronouncing Dictionary lookup
   - Example: "climate" → `['K', 'L', 'AY', 'M', 'AH', 'T']`
   - 135,000+ word database (automatic, no manual input)

2. **Observed Phonemes Detection:**
   - Audio → Wav2Vec2 model (`facebook/wav2vec2-lv-60-espeak-cv-ft`)
   - Acoustic analysis extracts phoneme sequence from waveform
   - Output: IPA phonemes converted to ARPAbet format

3. **Similarity Calculation:**
   - **Levenshtein Edit Distance** with weighted costs:
     - Substitution: 1.0 (wrong phoneme)
     - Deletion: 1.0 (missing phoneme)
     - Insertion: 0.5 (extra phoneme, less penalized)
   
   ```python
   similarity = 1.0 - (edit_distance / expected_length)
   pronunciation_score = similarity * 100
   ```

4. **Per-Word Scoring:**
   ```python
   if score >= 85: "Good pronunciation"
   elif score >= 70: "Understandable. Practice for clarity"
   elif score >= 40: "Several sounds unclear. Slow down"
   else: "Sounds very different from expected"
   ```

**Technical Details:**
- Model size: ~370MB (downloaded on first use)
- CPU inference: 2-5 seconds per audio clip
- CMU Dict fallback for unknown words

---

#### B. **Clarity Score** (0-100)
**Algorithm:** ASR confidence averaging

**Process:**
1. Whisper model transcribes audio with per-word confidence
2. Average confidence across all words × 100

```python
clarity_score = (sum(word.confidence for word in words) / len(words)) * 100
```

**Example:**
```json
{
  "words": [
    {"word": "hello", "confidence": 0.95},
    {"word": "world", "confidence": 0.89}
  ],
  "clarity_score": 92.0
}
```

---

#### C. **Fluency Metrics**

**1. Words Per Minute (WPM)**
```python
speech_duration = last_word.end - first_word.start
wpm = (total_words / speech_duration) * 60
```

**Benchmarks:**
- Slow: <120 WPM
- Conversational: 120-160 WPM
- Fast: >160 WPM

**2. Speech Duration vs Total Duration**
- Total duration: Full audio file length
- Speech duration: Only speaking time (excludes pauses)
- Silence ratio calculated for future pause analysis

---

#### D. **Transcript Match Score** (0-100)
**Algorithm:** Sequence alignment between expected and heard text

**Process:**
1. Normalize both texts (lowercase, remove punctuation)
2. SequenceMatcher algorithm (similar to diff)
3. Count matched vs mismatched words

```python
matcher = SequenceMatcher(expected_words, heard_words)
match_score = (matched_words / total_expected_words) * 100
```

**Mistake Detection:**
```json
{
  "expected_word": "subtle",
  "heard_word": "suttle",
  "feedback": "The word 'subtle' is often pronounced like 'suh-tl'; the b is silent."
}
```

---

## 2. 1v1 Battle

### Overview
Two players compete by recording the same prompt. Winner determined by pronunciation + clarity scores.

### Metrics

#### A. **Player Score** (Composite)
Each player receives:
1. **Pronunciation Score** (0-100) - Same algorithm as Pronunciation Practice
2. **Clarity Score** (0-100) - Whisper confidence average
3. **Pace WPM** - Speaking speed

#### B. **Star Verdicts** (Winner Selection)
Three categories decide stars:

**1. Pronunciation Star:**
```python
if abs(host_pron - opponent_pron) < 5:
    verdict = "tie"
elif host_pron > opponent_pron:
    verdict = "host"
else:
    verdict = "opponent"
```

**2. Clarity Star:**
```python
# Same tie/win logic with clarity scores
```

**3. Pace Star:**
```python
ideal_pace = 145 WPM  # Target conversational speed
host_deviation = abs(host_wpm - ideal_pace)
opponent_deviation = abs(opponent_wpm - ideal_pace)

# Winner = closer to ideal pace
```

#### C. **Overall Winner**
```python
# Count stars won by each player
if host_stars > opponent_stars: winner = "host"
elif opponent_stars > host_stars: winner = "opponent"
else: winner = "draw"
```

---

## 3. Group Debate

### Overview
Multi-participant debate with turn-based speaking. AI scores each turn automatically.

### Metrics

#### A. **AI Score per Turn** (0-100)

**New Algorithm (With Pronunciation Enabled):**
```python
pronunciation_score = assess_pronunciation(audio, transcribed_text)
clarity_score = average_whisper_confidence * 100

# Both available: average them
if pronunciation_score and clarity_score:
    ai_score = (pronunciation_score + clarity_score) / 2

# Only clarity available: use it directly
elif clarity_score:
    ai_score = clarity_score

# Neither available: flag as unavailable
else:
    ai_score = 0.0
    scoring_unavailable = True
```

**Components:**

**1. Pronunciation Score (0-100):**
- Transcribed text → CMU Dictionary → expected phonemes
- Audio → HF Wav2Vec2 → observed phonemes
- Levenshtein similarity → score

**2. Clarity Score (0-100):**
- Whisper ASR confidence average
- Measures how clearly words were recognized

**3. Fluency Metrics (Informational):**
- Words per minute
- Speech duration
- Total turn duration

#### B. **Winner Selection**
```python
# After all participants complete turns
winner = participant_with_highest_ai_score
```

#### C. **Teacher Override**
- Teachers can manually override AI scores
- `teacher_override_score` takes precedence in final display
- `teacher_comment` provides feedback text

---

## 4. Interview Studio (Gesture & Posture)

### Overview
Video analysis of body language, posture, eye contact, gestures, and facial expressions using MediaPipe computer vision.

### Architecture
- **ss3 Microservice:** Separate Python service running on port 8001
- **MediaPipe:** Google's pose/face/hand landmark detection models
- **Frame Sampling:** 5 FPS (5 frames per second analyzed)

---

### Metrics & Algorithms

#### A. **Posture Score** (0-100)
**Algorithm:** Geometric angle analysis of body alignment

**Landmarks Used:**
- Neck (nose to midpoint of shoulders)
- Shoulders (left/right shoulder landmarks)
- Hips (left/right hip landmarks)

**Process:**
1. **Neck-to-Shoulder Vector:**
   ```python
   neck_angle = angle_from_vertical(nose_landmark, shoulder_midpoint)
   
   # Thresholds
   max_deviation = 15°  # Maximum acceptable tilt
   
   if neck_angle <= max_deviation:
       neck_score = 100
   else:
       neck_score = max(0, 100 - (neck_angle - max_deviation) * penalty_factor)
   ```

2. **Shoulder-to-Hip Vector:**
   ```python
   torso_angle = angle_from_vertical(shoulder_midpoint, hip_midpoint)
   
   # Thresholds
   max_deviation = 10°  # Stricter than neck
   
   if torso_angle <= max_deviation:
       torso_score = 100
   else:
       torso_score = max(0, 100 - (torso_angle - max_deviation) * penalty_factor)
   ```

3. **Combined Posture Score:**
   ```python
   posture_score = (neck_score + torso_score) / 2
   ```

**Flags:**
- `ok`: Normal scoring applied
- `detection_failed`: Pose landmarks not detected
- `low_confidence`: Insufficient landmark quality
- `no_frames`: No valid frames sampled

---

#### B. **Eye Contact Score** (0-100)
**Algorithm:** Head orientation analysis using face mesh landmarks

**Measurements:**
1. **Head Yaw (Left-Right rotation):**
   ```python
   yaw_threshold = 15°  # Maximum acceptable deviation
   
   on_camera_frames = count(abs(yaw) <= yaw_threshold)
   ```

2. **Head Pitch (Up-Down tilt):**
   ```python
   pitch_threshold = 15°  # Maximum acceptable deviation
   
   on_camera_frames = count(abs(pitch) <= pitch_threshold)
   ```

3. **Score Calculation:**
   ```python
   on_camera_percentage = (on_camera_frames / total_frames) * 100
   eye_contact_score = on_camera_percentage
   ```

**Interpretation:**
- 90-100: Excellent eye contact (maintains camera focus)
- 70-89: Good (occasional glances away)
- 50-69: Moderate (frequent looking away)
- <50: Poor (mostly not looking at camera)

---

#### C. **Gesture Score** (0-100)
**Algorithm:** Hand-to-face proximity detection using hand landmarks

**Purpose:** Detect distracting gestures (touching face, hands near face)

**Process:**
1. **Hand Detection:**
   - MediaPipe Hand Landmarker detects hand keypoints
   - Tracks both left and right hands

2. **Face Detection:**
   - MediaPipe Face Mesh provides facial landmark positions

3. **Proximity Calculation:**
   ```python
   frame_diagonal = sqrt(width² + height²)
   proximity_threshold = 0.10 * frame_diagonal  # 10% of diagonal
   
   for each frame:
       for each hand:
           distance = euclidean(hand_center, face_center)
           if distance < proximity_threshold:
               distraction_count += 1
   
   distraction_percentage = (distraction_count / total_frames) * 100
   gesture_score = max(0, 100 - distraction_percentage)
   ```

**Scoring:**
- 90-100: Hands mostly away from face (professional)
- 70-89: Occasional face touching
- <70: Frequent distracting hand movements

---

#### D. **Stillness Score** (0-100)
**Algorithm:** Frame-to-frame motion variance analysis

**Purpose:** Detect excessive fidgeting or movement (nervous behavior)

**Process:**
1. **Motion Tracking:**
   ```python
   # Track centroid of pose landmarks across frames
   for each frame:
       centroid = average_position(all_pose_landmarks)
       displacement = distance(current_centroid, previous_centroid)
       displacements.append(displacement)
   ```

2. **Variance Calculation:**
   ```python
   motion_variance = variance(displacements)
   
   # Normalized thresholds
   variance_min = 0.0005  # Below this = perfect stillness (score 100)
   variance_max = 0.01    # Above this = excessive movement (score 0)
   ```

3. **Score Mapping:**
   ```python
   if motion_variance <= variance_min:
       stillness_score = 100
   elif motion_variance >= variance_max:
       stillness_score = 0
   else:
       # Linear interpolation
       ratio = (motion_variance - variance_min) / (variance_max - variance_min)
       stillness_score = 100 - (ratio * 100)
   ```

**Interpretation:**
- 90-100: Very calm, minimal movement
- 70-89: Some natural movement
- 50-69: Noticeable fidgeting
- <50: Excessive movement

---

#### E. **Facial Expression Score** (0-100)
**Algorithm:** Smile detection using mouth landmarks

**Process:**
1. **Smile Ratio Calculation:**
   ```python
   # MediaPipe Face Mesh landmarks
   mouth_corner_distance = distance(left_mouth_corner, right_mouth_corner)
   inter_eye_distance = distance(left_eye, right_eye)
   
   smile_ratio = mouth_corner_distance / inter_eye_distance
   
   # Threshold
   smile_threshold = 0.45  # Ratio above this = smiling
   ```

2. **Frame Analysis:**
   ```python
   smiling_frames = count(smile_ratio > smile_threshold)
   smile_percentage = (smiling_frames / total_frames) * 100
   
   # Cap at 80% (excessive smiling looks unnatural)
   capped_percentage = min(smile_percentage, 80)
   ```

3. **Score Calculation:**
   ```python
   # Linear rescale from 0-80% to 0-100 score
   facial_expression_score = (capped_percentage / 80) * 100
   ```

**Interpretation:**
- 80-100: Frequent, natural smiling (positive demeanor)
- 60-79: Moderate positive expression
- 40-59: Neutral expression
- <40: Serious/stern expression (may appear unfriendly)

---

#### F. **Overall Gesture Score** (0-100)
**Algorithm:** Weighted average of all 5 metrics

**Weights (Configurable):**
```yaml
posture:           0.20  (20%)
eye_contact:       0.25  (25%)
gesture:           0.20  (20%)
stillness:         0.15  (15%)
facial_expression: 0.20  (20%)
```

**Process:**
1. **Flag Filtering:**
   - Only metrics with `flag="ok"` participate
   - Metrics with `detection_failed`, `low_confidence`, or `no_frames` are excluded

2. **Weight Renormalization:**
   ```python
   surviving_metrics = [m for m in metrics if m.flag == "ok"]
   
   if not surviving_metrics:
       overall_score = 0
       session_flag = "low_confidence"
   else:
       # Renormalize weights to sum to 1.0
       total_weight = sum(weights[m.name] for m in surviving_metrics)
       
       for metric in surviving_metrics:
           applied_weight = weights[metric.name] / total_weight
       
       overall_score = sum(applied_weight * metric.score for each metric)
   ```

3. **Rounding:**
   ```python
   final_score = max(0, min(100, round(overall_score)))
   ```

**Example Calculation:**
```
Given:
- Posture: 85 (ok) → weight 0.20
- Eye Contact: 90 (ok) → weight 0.25
- Gesture: 78 (ok) → weight 0.20
- Stillness: 0 (detection_failed) → excluded
- Facial Expression: 88 (ok) → weight 0.20

Step 1: Filter out Stillness (flagged)
Step 2: Renormalize remaining weights:
  Total = 0.20 + 0.25 + 0.20 + 0.20 = 0.85
  
  Posture: 0.20/0.85 = 0.235
  Eye Contact: 0.25/0.85 = 0.294
  Gesture: 0.20/0.85 = 0.235
  Facial Expression: 0.20/0.85 = 0.235

Step 3: Weighted average:
  Overall = (85 × 0.235) + (90 × 0.294) + (78 × 0.235) + (88 × 0.235)
          = 19.975 + 26.46 + 18.33 + 20.68
          = 85.445
          ≈ 85 (rounded)
```

---

### MediaPipe Technical Details

**Models Used:**
- **Pose Landmarker:** 33 body keypoints (shoulders, hips, knees, etc.)
- **Face Mesh:** 468 facial landmarks (eyes, nose, mouth, contours)
- **Hand Landmarker:** 21 hand keypoints per hand

**Performance:**
- Frame rate: 5 FPS sampling (balance between accuracy and speed)
- Processing time: ~30-60 seconds for 2-minute video
- Model size: ~50MB combined (downloaded on first use)

**Reliability Flags:**
```python
if landmarks_confidence < threshold:
    flag = "low_confidence"
elif no_pose_detected:
    flag = "detection_failed"
elif sampled_frames == 0:
    flag = "no_frames"
else:
    flag = "ok"
```

---

## 5. Voice CruiseControl

### Overview
Voice-controlled navigation using continuous speech recognition.

### Metrics

#### A. **Recognition Accuracy**
**Algorithm:** Browser Web Speech API (Google Chrome)

**Process:**
- Real-time ASR with interim results
- Command matching against predefined menu options
- Fuzzy matching for partial/misheard commands

**No explicit scoring** - binary match (command recognized or not)

**Performance Metrics (Informational):**
- Recognition latency: ~500ms - 2s
- Command accuracy: Depends on microphone quality and ambient noise

---

## Technical Stack Summary

| Feature | ASR Model | Pronunciation | Computer Vision | Scoring Algorithm |
|---|---|---|---|---|
| **Pronunciation** | Whisper (small) | HF Wav2Vec2 + CMU Dict | N/A | Levenshtein similarity |
| **Battle** | Whisper | HF Wav2Vec2 | N/A | Star-based comparison |
| **Debate** | Whisper | HF Wav2Vec2 | N/A | Weighted average (pron + clarity) |
| **Interview** | N/A | N/A | MediaPipe (pose/face/hand) | Weighted average (5 metrics) |
| **CruiseControl** | Web Speech API | N/A | N/A | Command matching |

---

## Model Sizes & Performance

| Model | Size | First Load Time | Inference Time |
|---|---|---|---|
| **Whisper (small)** | ~140 MB | ~30s download | 2-5s per audio |
| **Wav2Vec2 Phoneme** | ~370 MB | ~60s download | 2-5s per audio |
| **MediaPipe Pose** | ~6 MB | Instant (built-in) | Real-time (30+ FPS) |
| **MediaPipe Face** | ~3 MB | Instant | Real-time |
| **MediaPipe Hands** | ~10 MB | Instant | Real-time |

**Total disk usage:** ~530 MB (models cached after first download)

---

## Scoring Transparency

All scores include:
- **Numeric value** (0-100 scale)
- **Interpretation label** (Excellent/Good/Fair/Poor)
- **Per-component breakdown** (where applicable)
- **Confidence flags** (detection_failed, low_confidence, etc.)

Students can see:
- Overall score
- Per-metric scores
- Feedback messages

Teachers can see:
- All of the above
- Raw metric values
- Applied weights
- Detection flags
- Per-frame analysis (Interview Studio)

---

## References & Citations

**Models:**
- OpenAI Whisper: https://github.com/openai/whisper
- HuggingFace Wav2Vec2: https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft
- MediaPipe: https://developers.google.com/mediapipe

**Datasets:**
- CMU Pronouncing Dictionary: http://www.speech.cs.cmu.edu/cgi-bin/cmudict

**Algorithms:**
- Levenshtein Distance: https://en.wikipedia.org/wiki/Levenshtein_distance
- SequenceMatcher: Python difflib standard library

---

**Document Version:** 1.0  
**Last Updated:** July 4, 2026  
**Platform:** KIET Soft Skills Training System
