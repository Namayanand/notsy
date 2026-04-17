package com.notsy.repository;

import com.notsy.entity.Notebook;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface NotebookRepository extends JpaRepository<Notebook, Long> {

    List<Notebook> findByUserIdOrderByCreatedAtDesc(Long userId);

    @Query("SELECT n FROM Notebook n WHERE n.id = :id AND n.user.id = :userId")
    Optional<Notebook> findByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);

    @Query("SELECT n FROM Notebook n WHERE n.id = :id")
    Optional<Notebook> findByIdWithUser(@Param("id") Long id);

    @Query("SELECT CASE WHEN COUNT(n) > 0 THEN true ELSE false END FROM Notebook n WHERE n.id = :id AND n.user.id = :userId")
    boolean existsByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);
}
