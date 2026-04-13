package com.notsy.service;

import com.notsy.dto.request.CreateNotebookRequest;
import com.notsy.dto.request.UpdateNotebookRequest;
import com.notsy.dto.response.NotebookResponse;
import com.notsy.entity.Notebook;
import com.notsy.entity.User;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.exception.UnauthorizedException;
import com.notsy.repository.NotebookRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class NotebookService {

    private final NotebookRepository notebookRepository;

    @Transactional(readOnly = true)
    public List<NotebookResponse> getAllNotebooks(User user) {
        return notebookRepository.findByUserIdOrderByCreatedAtDesc(user.getId())
                .stream()
                .map(this::toNotebookResponse)
                .collect(Collectors.toList());
    }

    @Transactional
    public NotebookResponse createNotebook(CreateNotebookRequest request, User user) {
        Notebook notebook = Notebook.builder()
                .title(request.getTitle())
                .description(request.getDescription())
                .colorTheme(request.getColorTheme())
                .isPublic(request.getIsPublic() != null ? request.getIsPublic() : false)
                .user(user)
                .build();

        notebook = notebookRepository.save(notebook);
        return toNotebookResponse(notebook);
    }

    @Transactional(readOnly = true)
    public NotebookResponse getNotebook(Long id, User user) {
        Notebook notebook = notebookRepository.findByIdAndUserId(id, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Notebook", id));
        return toNotebookResponse(notebook);
    }

    @Transactional
    public NotebookResponse updateNotebook(Long id, UpdateNotebookRequest request, User user) {
        Notebook notebook = notebookRepository.findByIdAndUserId(id, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Notebook", id));

        if (request.getTitle() != null) {
            notebook.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            notebook.setDescription(request.getDescription());
        }
        if (request.getColorTheme() != null) {
            notebook.setColorTheme(request.getColorTheme());
        }
        if (request.getIsPublic() != null) {
            notebook.setIsPublic(request.getIsPublic());
        }

        notebook = notebookRepository.save(notebook);
        return toNotebookResponse(notebook);
    }

    @Transactional
    public void deleteNotebook(Long id, User user) {
        Notebook notebook = notebookRepository.findByIdAndUserId(id, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Notebook", id));
        notebookRepository.delete(notebook);
    }

    public Notebook getNotebookEntity(Long id, User user) {
        return notebookRepository.findByIdAndUserId(id, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Notebook", id));
    }

    private NotebookResponse toNotebookResponse(Notebook notebook) {
        List<NotebookResponse.TopicSummaryResponse> topics = notebook.getTopics().stream()
                .map(topic -> NotebookResponse.TopicSummaryResponse.builder()
                        .id(topic.getId())
                        .title(topic.getTitle())
                        .orderIndex(topic.getOrderIndex())
                        .embeddingStatus(topic.getEmbeddingStatus().name())
                        .build())
                .collect(Collectors.toList());

        return NotebookResponse.builder()
                .id(notebook.getId())
                .title(notebook.getTitle())
                .description(notebook.getDescription())
                .colorTheme(notebook.getColorTheme())
                .isPublic(notebook.getIsPublic())
                .userId(notebook.getUser().getId())
                .topics(topics)
                .createdAt(notebook.getCreatedAt())
                .updatedAt(notebook.getUpdatedAt())
                .build();
    }
}
