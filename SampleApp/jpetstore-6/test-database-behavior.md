# Test Database Behavior Explanation

The test runs in this project do not leave new records in the database because:

1. All test classes (e.g., `AccountMapperTest`, `OrderMapperTest`) are annotated with `@Transactional`
2. In Spring Test context, `@Transactional` test methods roll back by default after each test
3. This is intentional behavior to ensure:
   - Tests don't pollute the database
   - Each test starts with a known database state
   - Tests can be run repeatedly without side effects

To verify this:
- Look at `AccountMapperTest.java` which has `@Transactional` annotation
- The test context in `MapperTestContext.java` configures transaction management
- Database operations like `insertAccount()` are performed within these transactional boundaries

If you need to keep test data in the database, you would need to either:
1. Add `@Rollback(false)` to specific test methods, or
2. Add `@Commit` annotation to override the default rollback behavior

However, it's generally recommended to keep the default rollback behavior for tests to maintain a clean test environment.