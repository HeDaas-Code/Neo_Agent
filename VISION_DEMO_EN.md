# Intelligent Agent Pseudo-Vision Feature Usage Demo

[中文](VISION_DEMO.md) | **English**

## Scenario Demonstrations

### Scenario 1: Environment Inquiry Conversation

**Without Vision Feature (Old Version):**
```
User: What's around you?
Xiao Ke: Around me... umm, just some everyday stuff, like books 
         and pens. What would you like to know?
```
❌ Vague response, lacks detail, unrealistic

**With Vision Feature (New Version):**
```
User: What's around you?

👁️ [Visual Perception] Environment: Xiao Ke's Room | Visible objects: 7

Xiao Ke: I looked around - there's a lot in the room!

         By the window is a white desk, about 120cm wide, with 
         various study supplies on it. To the right of the desk 
         against the wall is a four-tier white bookshelf filled 
         with books, especially history books - those are my 
         treasures!
         
         On the desk is my laptop, silver-colored, which I use 
         for research and study. There's also an eye-protection 
         lamp, though it's off now because the natural light 
         from the window is soft and bright enough.
         
         There's a potted plant on the windowsill, a small succulent, 
         very cute! The whole room has a warm, studious atmosphere 
         with a light scent of books - I really like this space!
```
✅ Specific and vivid, rich in detail, natural expression, immersive

---

### Scenario 2: Specific Object Inquiry

**Without Vision Feature:**
```
User: Do you have any books?
Xiao Ke: Yes, I have quite a few books, especially history books!
```
❌ Too simple, lacks detail

**With Vision Feature:**
```
User: Can you see any books?

👁️ [Visual Perception] Found: Bookshelf, 15+ books

Xiao Ke: Of course! There's a white bookshelf to the right of my 
         desk, four tiers high, full of books!
         
         The top tier has history books: "Records of the Ming Dynasty", 
         "History of the Qing Dynasty", "Modern Chinese History", etc. 
         The second tier has literature books, including "Dream of the 
         Red Chamber" and "Journey to the West" - classics! The third 
         tier has study materials and reference books, and the bottom 
         has some magazines and notebooks.
         
         Overall, there are probably over 20 books, mainly history and 
         literature. I love reading these! Want to know about any 
         specific book?
```
✅ Detailed description, organized by category, shows personal preferences

---

### Scenario 3: Environment Description

**Without Vision Feature:**
```
User: What does your room look like?
Xiao Ke: It's pretty ordinary, just a student's room with a desk, 
         bed, and bookshelf.
```
❌ Generic, boring, no characteristics

**With Vision Feature:**
```
User: What does your room look like?

👁️ [Visual Perception] Environment: Xiao Ke's Room | Full scan

Xiao Ke: My room faces southeast, so there's always nice natural light!

         The main furniture includes a white desk by the window, about 
         120cm wide. Next to it is a four-tier white bookshelf, full of 
         my favorite books. Behind me is my single bed with light blue 
         bedding, clean and tidy.
         
         There's a small potted succulent on the windowsill, very cute! 
         A beige curtain hangs by the window, though it's drawn back now 
         to let the sunshine in. The walls are light cream colored, giving 
         a warm, cozy feeling.
         
         Overall, the room isn't large but it's well-organized. I especially 
         like the soft natural light in the afternoon - perfect for reading 
         history books! The room has a light scent of books and occasionally 
         you can hear birds chirping outside - it's peaceful and comfortable.
```
✅ Comprehensive details, sensory description (sight, sound, smell), personal feelings

---

### Scenario 4: Object Detail Inquiry

**Without Vision Feature:**
```
User: What's on your desk?
Xiao Ke: There's a computer, lamp, and some books.
```
❌ List-like, lacks detail

**With Vision Feature:**
```
User: What's on your desk?

👁️ [Visual Perception] Scanning: White Desk surface objects

Xiao Ke: Let me see what's on my desk:

         On the left is my laptop, silver MacBook Air, which I use 
         daily for looking up information and studying. Next to it 
         is an eye-protection desk lamp, white with three brightness 
         levels, though it's off now.
         
         In the middle is a pencil holder with various pens - black 
         and blue gel pens, mechanical pencils, and highlighters. 
         There's also a sticky note pad with some study reminders.
         
         On the right are a few books I'm currently reading: one on 
         Ming Dynasty history and a Chinese language textbook. There's 
         also a water bottle - staying hydrated is important!
         
         Overall the desk is kept tidy, making it comfortable to study. 
         Everything has its place and is easy to find!
```
✅ Organized description, specific details, shows good habits

---

### Scenario 5: Atmosphere and Sensory Inquiry

**Without Vision Feature:**
```
User: How does your room feel?
Xiao Ke: It's quite comfortable, I like it!
```
❌ Too brief, no concrete feelings

**With Vision Feature:**
```
User: How does your room feel?

👁️ [Visual Perception] Environment: Overall atmosphere analysis

Xiao Ke: My room has a really warm, comfortable atmosphere!

         First, the light is great - facing southeast means morning 
         sunshine streams in, soft and not harsh. Afternoon light is 
         warm and golden, perfect for reading.
         
         There's always a light scent of books in the air, mixed with 
         the fresh smell from the potted plant on the windowsill - very 
         natural and pleasant. Occasionally you can hear birds chirping 
         outside, and when the wind blows, leaves rustle - it's peaceful.
         
         The room's color scheme is mainly white and cream, clean and 
         bright without being cold. The light blue bedding and green 
         plant add some color - simple yet cozy.
         
         Overall it's quiet and studious, making it easy to focus on 
         studying or reading. I really like this feeling - it's my own 
         little world!
```
✅ Multi-sensory description (sight, smell, sound), emotional resonance, vivid

---

## Feature Highlights

### 1. Automatic Trigger
- ✅ System automatically detects environment-related questions
- ✅ No manual commands needed
- ✅ Natural and smooth conversation flow

### 2. Rich Details
- ✅ Specific dimensions and colors
- ✅ Precise object positions
- ✅ Material and status descriptions

### 3. Multi-sensory
- ✅ Visual: appearance, color, layout
- ✅ Auditory: sounds in environment
- ✅ Olfactory: scents in environment
- ✅ Tactile: material texture

### 4. Emotional Expression
- ✅ Personal preferences and feelings
- ✅ Memories and stories about objects
- ✅ Emotional connection to environment

### 5. Natural Language
- ✅ Conversational, not mechanical
- ✅ Appropriate detail level
- ✅ Organized logic
- ✅ Engaging and interesting

---

## Usage Tips

### 1. Ask Environment Questions
- "What's around you?"
- "What can you see?"
- "Describe your environment"
- "What's in your room?"

### 2. Inquire About Specific Objects
- "Do you have any books?"
- "What's on your desk?"
- "Can you see a computer?"
- "What furniture is there?"

### 3. Ask for Details
- "What does [object] look like?"
- "Where is [object]?"
- "How big is [object]?"
- "What color is [object]?"

### 4. Explore Atmosphere
- "How does it feel there?"
- "What's the lighting like?"
- "Are there any sounds?"
- "What does it smell like?"

---

## Technical Features

### 1. Intelligent Recognition
```python
# Automatically detect environment-related keywords
keywords = ["around", "see", "environment", "room", "nearby"]
if any(keyword in user_input for keyword in keywords):
    trigger_vision_perception()
```

### 2. Structured Data
```json
{
  "environment": "Xiao Ke's Room",
  "description": "A bright room facing southeast",
  "objects": [
    {
      "name": "White Desk",
      "position": "By the window",
      "description": "Simple white desk",
      "size": "120cm x 60cm"
    }
  ]
}
```

### 3. Natural Generation
- Use LLM to generate natural responses
- Incorporate visual information into conversation
- Add personal feelings and stories
- Maintain consistent character personality

---

## Comparison

| Feature | Without Vision | With Vision |
|---------|---------------|-------------|
| **Detail Level** | Simple lists | Specific descriptions |
| **Realism** | Generic responses | Vivid details |
| **Engagement** | Boring | Interesting |
| **Immersion** | Low | High |
| **Information** | Limited | Rich |
| **Emotion** | None | Personal feelings |

---

## More Information

- [Feature Documentation](VISION_FEATURE_README_EN.md) - Complete feature description
- [Architecture Document](VISION_ARCHITECTURE.txt) - Technical implementation
- [Usage Examples](docs/EXAMPLES_EN.md) - More usage scenarios

---

<div align="center">

**Experience realistic AI perception!** 👁️✨

</div>
