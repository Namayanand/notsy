package com.notsy.service;

import com.notsy.dto.request.InviteMemberRequest;
import com.notsy.dto.response.MemberResponse;
import com.notsy.entity.Notebook;
import com.notsy.entity.NotebookMembership;
import com.notsy.entity.User;
import com.notsy.exception.BadRequestException;
import com.notsy.exception.ResourceNotFoundException;
import com.notsy.repository.NotebookMembershipRepository;
import com.notsy.repository.NotebookRepository;
import com.notsy.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class CollaborationService {

    private final NotebookMembershipRepository membershipRepository;
    private final NotebookRepository notebookRepository;
    private final UserRepository userRepository;
    private final NotificationService notificationService;

    @Transactional(readOnly = true)
    public List<MemberResponse> getMembers(Long notebookId, User user) {
        // Verify user has access
        if (!hasAccess(notebookId, user)) {
            throw new BadRequestException("You don't have access to this notebook");
        }

        return membershipRepository.findByNotebookId(notebookId)
            .stream()
            .map(this::toMemberResponse)
            .collect(Collectors.toList());
    }

    @Transactional
    public MemberResponse inviteMember(Long notebookId, InviteMemberRequest request, User user) {
        Notebook notebook = notebookRepository.findById(notebookId)
            .orElseThrow(() -> new ResourceNotFoundException("Notebook", notebookId));

        // Check if current user is owner
        NotebookMembership ownerMembership = membershipRepository
            .findByNotebookIdAndUserId(notebookId, user.getId())
            .orElseThrow(() -> new BadRequestException("You don't have access to this notebook"));

        if (ownerMembership.getRole() != NotebookMembership.Role.OWNER) {
            throw new BadRequestException("Only the notebook owner can invite members");
        }

        // Find user by email
        User invitedUser = userRepository.findByEmailIgnoreCase(request.getEmail())
            .orElseThrow(() -> new BadRequestException("User with email " + request.getEmail() + " not found"));

        // Check if already a member
        if (membershipRepository.findByNotebookIdAndUserId(notebookId, invitedUser.getId()).isPresent()) {
            throw new BadRequestException("User is already a member of this notebook");
        }

        NotebookMembership.Role role = NotebookMembership.Role.valueOf(request.getRole().toUpperCase());

        NotebookMembership membership = NotebookMembership.builder()
            .notebook(notebook)
            .user(invitedUser)
            .role(role)
            .build();

        membership = membershipRepository.save(membership);

        // Send notification
        notificationService.sendNotification(
            invitedUser,
            com.notsy.entity.Notification.NotificationType.COLLABORATOR_JOINED,
            "You've been added to " + notebook.getTitle(),
            user.getEmail() + " added you as " + role.name().toLowerCase() + " to notebook \"" + notebook.getTitle() + "\"",
            notebookId,
            null
        );

        log.info("User {} invited {} as {} to notebook {}",
            user.getId(), invitedUser.getId(), role, notebookId);

        return toMemberResponse(membership);
    }

    @Transactional
    public void removeMember(Long notebookId, Long memberId, User user) {
        NotebookMembership ownerMembership = membershipRepository
            .findByNotebookIdAndUserId(notebookId, user.getId())
            .orElseThrow(() -> new BadRequestException("You don't have access to this notebook"));

        if (ownerMembership.getRole() != NotebookMembership.Role.OWNER) {
            throw new BadRequestException("Only the notebook owner can remove members");
        }

        NotebookMembership targetMembership = membershipRepository
            .findByNotebookIdAndUserId(notebookId, memberId)
            .orElseThrow(() -> new ResourceNotFoundException("Member", memberId));

        if (targetMembership.getRole() == NotebookMembership.Role.OWNER) {
            throw new BadRequestException("Cannot remove the notebook owner");
        }

        membershipRepository.delete(targetMembership);
        log.info("User {} removed member {} from notebook {}", user.getId(), memberId, notebookId);
    }

    @Transactional
    public void updateMemberRole(Long notebookId, Long memberId, String newRole, User user) {
        NotebookMembership ownerMembership = membershipRepository
            .findByNotebookIdAndUserId(notebookId, user.getId())
            .orElseThrow(() -> new BadRequestException("You don't have access to this notebook"));

        if (ownerMembership.getRole() != NotebookMembership.Role.OWNER) {
            throw new BadRequestException("Only the notebook owner can change member roles");
        }

        NotebookMembership targetMembership = membershipRepository
            .findByNotebookIdAndUserId(notebookId, memberId)
            .orElseThrow(() -> new ResourceNotFoundException("Member", memberId));

        targetMembership.setRole(NotebookMembership.Role.valueOf(newRole.toUpperCase()));
        membershipRepository.save(targetMembership);
        log.info("User {} updated member {} role to {} in notebook {}",
            user.getId(), memberId, newRole, notebookId);
    }

    @Transactional(readOnly = true)
    public boolean hasAccess(Long notebookId, User user) {
        // Owner has access
        if (membershipRepository.isOwner(notebookId, user.getId())) {
            return true;
        }
        // Member has access
        if (membershipRepository.isMember(notebookId, user.getId())) {
            return true;
        }
        // Public notebook (check notebook.isPublic)
        Notebook notebook = notebookRepository.findById(notebookId).orElse(null);
        return notebook != null && Boolean.TRUE.equals(notebook.getIsPublic());
    }

    @Transactional(readOnly = true)
    public NotebookMembership.Role getMembershipRole(Long notebookId, Long userId) {
        return membershipRepository.findByNotebookIdAndUserId(notebookId, userId)
            .map(NotebookMembership::getRole)
            .orElse(null);
    }

    private MemberResponse toMemberResponse(NotebookMembership m) {
        User u = m.getUser();
        return MemberResponse.builder()
            .id(m.getId())
            .userId(u.getId())
            .email(u.getEmail())
            .name(u.getName())
            .role(m.getRole().name())
            .joinedAt(m.getJoinedAt())
            .build();
    }
}
