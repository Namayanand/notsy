package com.notsy.service;

import com.notsy.dto.request.CreateNotebookRequest;
import com.notsy.dto.request.UpdateNotebookRequest;
import com.notsy.dto.response.NotebookResponse;
import com.notsy.entity.Notebook;
import com.notsy.entity.NotebookMembership;
import com.notsy.entity.User;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.exception.UnauthorizedException;
import com.notsy.repository.NotebookMembershipRepository;
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
    private final NotebookMembershipRepository membershipRepository;

    @Transactional(readOnly = true)
    public List<NotebookResponse> getAllNotebooks(User user) {
        // Get notebooks owned by user
        List<Notebook> owned = notebookRepository.findByUserIdOrderByCreatedAtDesc(user.getId());

        // Get notebooks where user is a member (with notebook eagerly loaded)
        List<NotebookMembership> memberships = membershipRepository.findByUserIdWithNotebook(user.getId());

        // Combine and remove duplicates by ID
        List<Long> addedIds = new java.util.ArrayList<>();
        List<NotebookResponse> results = new java.util.ArrayList<>();

        // Add owned notebooks
        for (Notebook nb : owned) {
            if (!addedIds.contains(nb.getId())) {
                addedIds.add(nb.getId());
                results.add(buildNotebookResponse(nb, user, false, null));
            }
        }

        // Add shared notebooks
        for (NotebookMembership m : memberships) {
            Notebook nb = m.getNotebook();
            if (!addedIds.contains(nb.getId())) {
                addedIds.add(nb.getId());
                results.add(buildNotebookResponse(nb, user, true, m.getRole().name()));
            }
        }

        // Sort by createdAt desc
        results.sort((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()));

        return results;
    }

    private NotebookResponse buildNotebookResponse(Notebook notebook, User currentUser, boolean isShared, String role) {
        List<NotebookMembership> allMemberships = membershipRepository.findByNotebookId(notebook.getId());
        List<NotebookResponse.MemberInfo> members = allMemberships.stream()
                .map(m -> NotebookResponse.MemberInfo.builder()
                        .userId(m.getUser().getId())
                        .name(m.getUser().getName())
                        .email(m.getUser().getEmail())
                        .role(m.getRole().name())
                        .build())
                .collect(Collectors.toList());

        return NotebookResponse.builder()
                .id(notebook.getId())
                .title(notebook.getTitle())
                .description(notebook.getDescription())
                .colorTheme(notebook.getColorTheme())
                .isPublic(notebook.getIsPublic())
                .userId(notebook.getUser().getId())
                .owner(NotebookResponse.OwnerInfo.builder()
                        .id(notebook.getUser().getId())
                        .name(notebook.getUser().getName())
                        .email(notebook.getUser().getEmail())
                        .build())
                .topics(java.util.Collections.emptyList())
                .members(members)
                .createdAt(notebook.getCreatedAt())
                .updatedAt(notebook.getUpdatedAt())
                .isShared(isShared)
                .sharedRole(role)
                .build();
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

        // Create ownership membership
        NotebookMembership membership = NotebookMembership.builder()
                .notebook(notebook)
                .user(user)
                .role(NotebookMembership.Role.OWNER)
                .build();
        membershipRepository.save(membership);

        // Build response directly without re-fetching
        return NotebookResponse.builder()
                .id(notebook.getId())
                .title(notebook.getTitle())
                .description(notebook.getDescription())
                .colorTheme(notebook.getColorTheme())
                .isPublic(notebook.getIsPublic())
                .userId(user.getId())
                .owner(NotebookResponse.OwnerInfo.builder()
                        .id(user.getId())
                        .name(user.getName())
                        .email(user.getEmail())
                        .build())
                .topics(java.util.Collections.emptyList())
                .createdAt(notebook.getCreatedAt())
                .updatedAt(notebook.getUpdatedAt())
                .isShared(false)
                .sharedRole("OWNER")
                .build();
    }

    @Transactional(readOnly = true)
    public NotebookResponse getNotebook(Long id, User user) {
        // Check if user owns the notebook
        var owned = notebookRepository.findByIdAndUserId(id, user.getId());
        if (owned.isPresent()) {
            Notebook nb = owned.get();
            // Access user to ensure it's loaded
            nb.getUser().getId();
            return buildNotebookResponse(nb, user, false, "OWNER");
        }

        // Check if user is a member of the notebook
        var membership = membershipRepository.findByNotebookIdAndUserId(id, user.getId());
        if (membership.isPresent()) {
            Notebook nb = membership.get().getNotebook();
            // Access user to ensure it's loaded
            nb.getUser().getId();
            return buildNotebookResponse(nb, user, true, membership.get().getRole().name());
        }

        throw new ResourceNotFoundException("Notebook", id);
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
        return buildNotebookResponse(notebook, user, false, "OWNER");
    }

    @Transactional
    public void deleteNotebook(Long id, User user) {
        Notebook notebook = notebookRepository.findByIdAndUserId(id, user.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Notebook", id));
        notebookRepository.delete(notebook);
    }

    public Notebook getNotebookEntity(Long id, User user) {
        // Check if user owns the notebook
        var owned = notebookRepository.findByIdAndUserId(id, user.getId());
        if (owned.isPresent()) {
            return owned.get();
        }

        // Check if user is a member of the notebook
        var membership = membershipRepository.findByNotebookIdAndUserId(id, user.getId());
        if (membership.isPresent()) {
            return membership.get().getNotebook();
        }

        throw new ResourceNotFoundException("Notebook", id);
    }

    private NotebookResponse toNotebookResponse(Notebook notebook) {
        return toNotebookResponse(notebook, null);
    }

    private NotebookResponse toNotebookResponse(Notebook notebook, User currentUser) {
        List<NotebookResponse.TopicSummaryResponse> topics = notebook.getTopics().stream()
                .map(topic -> NotebookResponse.TopicSummaryResponse.builder()
                        .id(topic.getId())
                        .title(topic.getTitle())
                        .orderIndex(topic.getOrderIndex())
                        .embeddingStatus(topic.getEmbeddingStatus().name())
                        .build())
                .collect(Collectors.toList());

        var builder = NotebookResponse.builder()
                .id(notebook.getId())
                .title(notebook.getTitle())
                .description(notebook.getDescription())
                .colorTheme(notebook.getColorTheme())
                .isPublic(notebook.getIsPublic())
                .userId(notebook.getUser().getId())
                .owner(NotebookResponse.OwnerInfo.builder()
                        .id(notebook.getUser().getId())
                        .name(notebook.getUser().getName())
                        .email(notebook.getUser().getEmail())
                        .build())
                .topics(topics)
                .createdAt(notebook.getCreatedAt())
                .updatedAt(notebook.getUpdatedAt());

        // Check if shared with current user
        if (currentUser != null && !notebook.getUser().getId().equals(currentUser.getId())) {
            var membership = membershipRepository.findByNotebookIdAndUserId(notebook.getId(), currentUser.getId());
            if (membership.isPresent()) {
                builder.isShared(true)
                        .sharedRole(membership.get().getRole().name());
            }
        }

        return builder.build();
    }
}
