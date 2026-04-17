package com.notsy.repository;

import com.notsy.entity.NotebookMembership;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface NotebookMembershipRepository extends JpaRepository<NotebookMembership, Long> {

    @Query("SELECT nm FROM NotebookMembership nm JOIN FETCH nm.user WHERE nm.notebook.id = :notebookId")
    List<NotebookMembership> findByNotebookId(@Param("notebookId") Long notebookId);

    @Query("SELECT nm FROM NotebookMembership nm JOIN FETCH nm.notebook JOIN FETCH nm.notebook.user WHERE nm.user.id = :userId")
    List<NotebookMembership> findByUserIdWithNotebook(@Param("userId") Long userId);

    @Query("SELECT nm FROM NotebookMembership nm WHERE nm.notebook.id = :notebookId AND nm.user.id = :userId")
    Optional<NotebookMembership> findByNotebookIdAndUserId(@Param("notebookId") Long notebookId, @Param("userId") Long userId);

    @Query("SELECT COUNT(nm) > 0 FROM NotebookMembership nm WHERE nm.notebook.id = :notebookId AND nm.user.id = :userId")
    boolean isMember(@Param("notebookId") Long notebookId, @Param("userId") Long userId);

    @Query("SELECT CASE WHEN nm.role = 'OWNER' THEN true ELSE false END FROM NotebookMembership nm WHERE nm.notebook.id = :notebookId AND nm.user.id = :userId")
    boolean isOwner(@Param("notebookId") Long notebookId, @Param("userId") Long userId);

    void deleteByNotebookIdAndUserId(Long notebookId, Long userId);
}
