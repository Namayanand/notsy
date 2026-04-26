package com.notsy.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.notsy.dto.request.CreateQuizRequest;
import com.notsy.dto.request.SubmitQuizAnswerRequest;
import com.notsy.dto.response.QuizResponse;
import com.notsy.dto.response.QuizResponse.*;
import com.notsy.entity.*;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class QuizService {

    private final QuizRepository quizRepository;
    private final QuizQuestionRepository quizQuestionRepository;
    private final TopicRepository topicRepository;
    private final UserRepository userRepository;
    private final FlashcardRepository flashcardRepository;
    private final ObjectMapper objectMapper;

    private static final String AI_SERVICE_URL = System.getenv("AI_SERVICE_URL") != null
        ? System.getenv("AI_SERVICE_URL") : "http://localhost:8000";

    @Transactional
    public QuizResponse generateQuiz(CreateQuizRequest request, User user) {
        Topic topic = topicRepository.findByIdAndUserId(request.getTopicId(), user.getId())
            .orElseThrow(() -> new ResourceNotFoundException("Topic", request.getTopicId()));

        Quiz.QuizType quizType = request.getQuizType() != null
            ? Quiz.QuizType.valueOf(request.getQuizType().toUpperCase())
            : Quiz.QuizType.MIXED;

        int difficultyTier = request.getDifficultyTier() != null
            ? request.getDifficultyTier()
            : calculateAdaptiveDifficulty(topic.getId(), user.getId());

        // Call AI service to generate questions
        List<Map<String, Object>> generatedQuestions = callQuizGeneration(topic, user, quizType, difficultyTier,
            request.getQuestionCount() != null ? request.getQuestionCount() : 10);

        Quiz quiz = Quiz.builder()
            .title(request.getTitle() != null ? request.getTitle() : "Quiz on " + topic.getTitle())
            .quizType(quizType)
            .topic(topic)
            .user(user)
            .difficultyTier(difficultyTier)
            .build();

        quiz = quizRepository.save(quiz);

        for (Map<String, Object> qData : generatedQuestions) {
            QuizQuestion question = QuizQuestion.builder()
                .question((String) qData.get("question"))
                .questionType(QuizQuestion.QuestionType.valueOf(
                    qData.getOrDefault("type", "MCQ").toString().toUpperCase()))
                .answer((String) qData.get("answer"))
                .options(qData.get("options") != null ? qData.get("options").toString() : null)
                .areaCovered((String) qData.get("area"))
                .difficultyTier(difficultyTier)
                .quiz(quiz)
                .build();
            quizQuestionRepository.save(question);
            quiz.getQuestions().add(question);
        }

        return toResponse(quiz);
    }

    @Transactional
    public QuizResponse submitAnswer(Long quizId, SubmitQuizAnswerRequest request, User user) {
        Quiz quiz = quizRepository.findByIdWithQuestions(quizId)
            .orElseThrow(() -> new ResourceNotFoundException("Quiz", quizId));

        if (!quiz.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("Quiz", quizId);
        }

        QuizQuestion question = quizQuestionRepository.findById(request.getQuestionId())
            .orElseThrow(() -> new ResourceNotFoundException("Question", request.getQuestionId()));

        if (!question.getQuiz().getId().equals(quizId)) {
            throw new BadRequestException("Question does not belong to this quiz");
        }

        boolean isCorrect = question.getAnswer().equalsIgnoreCase(request.getAnswer().trim());
        question.setUserAnswer(request.getAnswer());
        question.setIsCorrect(isCorrect);
        quizQuestionRepository.save(question);

        // Update running score
        int correctCount = (int) quiz.getQuestions().stream()
            .filter(q -> q.getIsCorrect() != null && q.getIsCorrect()).count();
        quiz.setTotalScore(correctCount);
        quiz.setMaxScore(quiz.getQuestions().size());
        quizRepository.save(quiz);

        return toResponse(quiz);
    }

    @Transactional
    public QuizResponse completeQuiz(Long quizId, User user) {
        Quiz quiz = quizRepository.findByIdWithQuestions(quizId)
            .orElseThrow(() -> new ResourceNotFoundException("Quiz", quizId));

        if (!quiz.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("Quiz", quizId);
        }

        quiz.setCompletedAt(LocalDateTime.now());
        quiz.setTotalScore((int) quiz.getQuestions().stream()
            .filter(q -> q.getIsCorrect() != null && q.getIsCorrect()).count());
        quiz.setMaxScore(quiz.getQuestions().size());

        // Calculate weak areas
        Map<String, Long> areaCorrect = new HashMap<>();
        Map<String, Long> areaTotal = new HashMap<>();
        for (QuizQuestion q : quiz.getQuestions()) {
            String area = q.getAreaCovered() != null ? q.getAreaCovered() : "general";
            areaTotal.merge(area, 1L, Long::sum);
            if (Boolean.TRUE.equals(q.getIsCorrect())) {
                areaCorrect.merge(area, 1L, Long::sum);
            }
        }

        List<Map<String, Object>> weakAreas = new ArrayList<>();
        for (String area : areaTotal.keySet()) {
            long total = areaTotal.get(area);
            long correct = areaCorrect.getOrDefault(area, 0L);
            double accuracy = (double) correct / total;
            if (accuracy < 0.7) {
                weakAreas.add(Map.of("area", area, "accuracy", accuracy, "correct", correct, "total", total));
            }
        }

        try {
            quiz.setWeakAreas(objectMapper.writeValueAsString(weakAreas));
        } catch (Exception e) {
            log.error("Failed to serialize weak areas", e);
        }

        // Update adaptive difficulty
        updateAdaptiveDifficulty(quiz.getTopic().getId(), user.getId(), quiz);

        quiz = quizRepository.save(quiz);
        return toResponse(quiz);
    }

    @Transactional(readOnly = true)
    public List<QuizResponse> getQuizzesByTopic(Long topicId, User user) {
        return quizRepository.findByTopicIdAndUserId(topicId, user.getId())
            .stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public QuizResponse getQuiz(Long quizId, User user) {
        Quiz quiz = quizRepository.findByIdWithQuestions(quizId)
            .orElseThrow(() -> new ResourceNotFoundException("Quiz", quizId));

        if (!quiz.getUser().getId().equals(user.getId())) {
            throw new ResourceNotFoundException("Quiz", quizId);
        }

        return toResponse(quiz);
    }

    @Transactional(readOnly = true)
    public List<String> getWeakAreas(Long topicId, User user) {
        List<Quiz> quizzes = quizRepository.findCompletedByTopicIdAndUserId(topicId, user.getId());
        if (quizzes.isEmpty()) {
            return Collections.emptyList();
        }

        Set<String> weakAreas = new LinkedHashSet<>();
        for (Quiz quiz : quizzes) {
            if (quiz.getWeakAreas() != null) {
                try {
                    List<Map<String, Object>> areas = objectMapper.readValue(
                        quiz.getWeakAreas(), new TypeReference<List<Map<String, Object>>>() {});
                    for (Map<String, Object> area : areas) {
                        weakAreas.add((String) area.get("area"));
                    }
                } catch (Exception e) {
                    log.error("Failed to parse weak areas", e);
                }
            }
        }
        return new ArrayList<>(weakAreas);
    }

    private int calculateAdaptiveDifficulty(Long topicId, Long userId) {
        List<Quiz> quizzes = quizRepository.findCompletedByTopicIdAndUserId(topicId, userId);
        if (quizzes.isEmpty()) {
            return 2; // default medium
        }

        double avgAccuracy = quizzes.stream()
            .filter(q -> q.getTotalScore() != null && q.getMaxScore() != null && q.getMaxScore() > 0)
            .mapToDouble(q -> (double) q.getTotalScore() / q.getMaxScore())
            .average().orElse(0.5);

        if (avgAccuracy > 0.85) return 3; // hard
        if (avgAccuracy < 0.5) return 1;  // easy
        return 2;                          // medium
    }

    private void updateAdaptiveDifficulty(Long topicId, Long userId, Quiz quiz) {
        // Adaptive difficulty is automatically considered on next quiz generation
        // via calculateAdaptiveDifficulty - nothing to persist separately
    }

    private List<Map<String, Object>> callQuizGeneration(Topic topic, User user,
                                                        Quiz.QuizType quizType,
                                                        int difficultyTier,
                                                        int questionCount) {
        try {
            RestTemplate restTemplate = new RestTemplate();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> requestBody = Map.of(
                "topic_id", topic.getId(),
                "topic_title", topic.getTitle(),
                "topic_description", topic.getDescription() != null ? topic.getDescription() : "",
                "quiz_type", quizType.name(),
                "difficulty_tier", difficultyTier,
                "question_count", questionCount,
                "mode", "quiz_generation"
            );

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);
            ResponseEntity<Map> response = restTemplate.exchange(
                AI_SERVICE_URL + "/generate_quiz",
                HttpMethod.POST,
                entity,
                Map.class
            );

            if (response.getBody() != null && response.getBody().get("questions") != null) {
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> questions = (List<Map<String, Object>>) response.getBody().get("questions");
                return questions;
            }
        } catch (Exception e) {
            log.error("Failed to call quiz generation AI service: {}", e.getMessage());
        }

        // Return empty list on failure - caller should handle
        return Collections.emptyList();
    }

    private QuizResponse toResponse(Quiz quiz) {
        List<QuizQuestionResponse> questionResponses = quiz.getQuestions().stream()
            .map(q -> QuizQuestionResponse.builder()
                .id(q.getId())
                .question(q.getQuestion())
                .questionType(q.getQuestionType().name())
                .answer(quiz.getCompletedAt() != null ? q.getAnswer() : null) // Only show after completion
                .options(q.getOptions())
                .isCorrect(q.getIsCorrect())
                .userAnswer(q.getUserAnswer())
                .difficultyTier(q.getDifficultyTier())
                .areaCovered(q.getAreaCovered())
                .build())
            .collect(Collectors.toList());

        return QuizResponse.builder()
            .id(quiz.getId())
            .title(quiz.getTitle())
            .quizType(quiz.getQuizType().name())
            .topicId(quiz.getTopic().getId())
            .totalScore(quiz.getTotalScore())
            .maxScore(quiz.getMaxScore())
            .difficultyTier(quiz.getDifficultyTier())
            .questions(questionResponses)
            .completedAt(quiz.getCompletedAt())
            .createdAt(quiz.getCreatedAt())
            .build();
    }
}
