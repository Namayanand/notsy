# Conversation Branching Feature Implementation

## Context
The user wants to branch conversations from specific text selections within AI messages. For example:
- Chat about "machine learning" → AI mentions "gradient descent"
- User selects "gradient descent" → can start a branched chat
- The text "gradient descent" should be highlighted in the parent conversation
- Clicking the highlighted text should navigate to the branched chat
- User can navigate back to parent chat

The backend already stores branch metadata (selectionStart, selectionEnd, parentMessageId). The frontend has basic branching UI but lacks:
1. Visual highlighting of branched text in parent conversation
2. Click-to-navigate to branched chat
3. Proper text selection tracking

## Implementation Plan

### Phase 1: Backend Enhancement
**File: `backend/src/main/java/com/notsy/dto/response/MessageResponse.java`**
- Add `hasBranches: boolean` field to indicate if message has child branches

**File: `backend/src/main/java/com/notsy/dto/response/MessageBranchInfo.java` (new)**
- Create DTO for branch info: branchId, branchConversationId, selectionStart, selectionEnd, title

**File: `backend/src/main/java/com/notsy/repository/ConversationBranchRepository.java`**
- Add method: `findByParentMessageId(Long messageId)` to get branches for a message

**File: `backend/src/main/java/com/notsy/service/ConversationService.java`**
- Modify `toMessageResponse()` to include branch info for each message

### Phase 2: Frontend - Track Message Branches
**File: `frontend/src/components/ChatInterface.jsx`**

1. Update state to track message branches:
   ```javascript
   const [messageBranchesMap, setMessageBranchesMap] = useState({}); // messageId -> array of branches
   ```

2. Create `loadMessageBranches()` function that loads branches for all messages in conversation

3. Modify `loadConversation()` to also load message branches

### Phase 3: Frontend - Highlight Branched Text
**File: `frontend/src/components/ChatInterface.jsx`**

1. Create a new `renderMessageContentWithBranches()` function that:
   - Takes message content and branch info
   - Wraps branched text in a `<span className="branched-text">` 
   - Adds onClick handler to navigate to branch

2. Update the message rendering to use this new function for AI messages

3. Add CSS for highlighting:
   - Background color (e.g., light purple)
   - Underline or border
   - Cursor pointer
   - Hover effect

### Phase 4: Frontend - Navigation
**File: `frontend/src/components/ChatInterface.jsx`**

1. Add `handleNavigateToBranch(branchId)` function that:
   - Sets the current conversation to the branch
   - Loads branch messages
   - Updates breadcrumb

2. Update breadcrumb to properly navigate to any ancestor (not just parent)

## Files to Modify

1. `backend/src/main/java/com/notsy/dto/response/MessageResponse.java` - Add hasBranches field
2. `backend/src/main/java/com/notsy/repository/ConversationBranchRepository.java` - Add query method
3. `backend/src/main/java/com/notsy/service/ConversationService.java` - Include branch info in messages
4. `frontend/src/components/ChatInterface.jsx` - Main UI changes
5. `frontend/src/components/ChatInterface.css` - Add highlight styles

## Testing

1. Start a conversation about a topic
2. Wait for AI response containing distinct text (e.g., "gradient descent")
3. Select that text in the AI message
4. Create a branch with context
5. Verify the text is now highlighted in the parent conversation
6. Click the highlighted text → should navigate to the branch
7. Click "Back to Parent" → should return to original conversation with highlighted text