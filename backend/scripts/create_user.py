"""Admin user oluşturucu CLI.

Kullanım:
    docker compose exec backend uv run python scripts/create_user.py \\
        --email me@example.com --password 'güçlü-şifre' \\
        [--full-name "Johnson"] [--is-admin]

Idempotent değil — aynı email ikinci kez denenirse 409 hatası, exit 1.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.exceptions import ConflictError
from app.db.session import AsyncSessionLocal
from app.services.auth_service import register_user


async def main(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        try:
            user = await register_user(
                session=session,
                email=args.email,
                password=args.password,
                full_name=args.full_name,
                is_admin=args.is_admin,
            )
        except ConflictError as e:
            print(f"✗ {e.message} (email: {args.email})", file=sys.stderr)
            return 1

    print("✓ Kullanıcı oluşturuldu")
    print(f"  email:     {user.email}")
    print(f"  id:        {user.id}")
    print(f"  full_name: {user.full_name}")
    print(f"  is_admin:  {user.is_admin}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MarketLens admin user oluşturucu",
    )
    parser.add_argument("--email", required=True, help="Kullanıcı email adresi")
    parser.add_argument("--password", required=True, help="Kullanıcı şifresi (min 8 karakter)")
    parser.add_argument("--full-name", default=None, help="İsteğe bağlı tam ad")
    parser.add_argument(
        "--is-admin",
        action="store_true",
        help="is_admin = true (RBAC henüz aktif değil, gelecek için işaretler)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args)))
