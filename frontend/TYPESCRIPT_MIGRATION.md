# TypeScript Migration Guide

This project now has TypeScript baseline support. This guide explains how to gradually migrate from JavaScript to TypeScript.

## Quick Start

1. **Type checking**: Run `npm run type-check` to check types without emitting files
2. **Build**: Run `npm run build` to build with TypeScript compilation
3. **Development**: Continue using `npm run dev` - Vite handles both JS and TS files

## Migration Strategy

### Phase 1: Start with new files (CURRENT)
- Create new components as `.tsx` files
- Use types from `src/types/index.ts`
- Keep existing `.jsx` files as-is

### Phase 2: Convert utilities and services
- Convert `src/utils/` files to `.ts`
- Convert `src/services/` files to `.ts`
- Add proper type annotations

### Phase 3: Convert components gradually
- Start with leaf components (no children)
- Move to container components
- Convert one file at a time, test thoroughly

## Available Types

Common types are available in `src/types/index.ts`:

```typescript
import { User, Content, Goal, Notification } from '@/types';
```

## Path Aliases

TypeScript is configured with path aliases:

```typescript
import Button from '@/components/Button';
import { apiClient } from '@/services/api';
import { PLATFORMS } from '@/constants/app';
```

## Best Practices

1. **Start strict**: Types are configured strictly - fix all issues
2. **Use interfaces**: Prefer interfaces over types for object shapes
3. **Type props**: Always type component props
4. **Avoid `any`**: Use proper types or `unknown`
5. **Export types**: Export types alongside components when needed

## Example Migration

Before (JS):
```javascript
// components/UserCard.jsx
const UserCard = ({ user, onClick }) => {
  return (
    <div onClick={() => onClick(user.id)}>
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  );
};
```

After (TS):
```typescript
// components/UserCard.tsx
import { User } from '@/types';

interface UserCardProps {
  user: User;
  onClick: (userId: number) => void;
}

const UserCard: React.FC<UserCardProps> = ({ user, onClick }) => {
  return (
    <div onClick={() => onClick(user.id)}>
      <h3>{user.full_name || user.username}</h3>
      <p>{user.email}</p>
    </div>
  );
};

export default UserCard;
```

## Configuration Files

- `tsconfig.json`: Main TypeScript configuration
- `tsconfig.node.json`: Node.js specific configuration
- Path aliases configured for easy imports

## Commands

- `npm run type-check`: Check types without building
- `npm run build`: Build with TypeScript compilation
- `npm run dev`: Development with hot reload (supports both JS and TS)

## Notes

- Mixed JS/TS is supported during migration
- All existing JavaScript files continue to work
- TypeScript is opt-in per file
- Vite handles compilation automatically