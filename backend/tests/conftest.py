"""Pytest fixtures with isolated databases for application API tests."""

import os
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# Ensure backend root is on Python module path before importing the application.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.models  # noqa: F401 - register every ORM table with Base metadata
from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.base_class import Base
from app.main import app
from app.models.auction import Auction, AuctionStatus
from app.models.audit_log import AuditLog
from app.models.bid import Bid
from app.models.category import Category
from app.models.notification import Notification
from app.models.product import Product, ProductCondition
from app.models.role import Role
from app.models.seller_payment_profile import (
    SellerPaymentProfile,
    SellerPaymentSetupMode,
    SellerPaymentSetupStatus,
)
from app.models.transaction import (
    PaymentAttempt,
    PaymentStatus,
    SettlementType,
    Transaction,
)
from app.models.user import User, UserStatus
from app.models.watchlist import Watchlist


TEST_PASSWORD = "password123"
MYSQL_TEST_DATABASE = "bidsmart_concurrency_test"
MYSQL_TEST_WRITE_OPT_IN = "I_UNDERSTAND_THIS_IS_DISPOSABLE"


@lru_cache(maxsize=1)
def _test_password_hash() -> str:
    return get_password_hash(TEST_PASSWORD)


def _seed_marketplace(db: Session) -> None:
    """Create deterministic records used by API tests instead of relying on app data."""
    roles = {
        "ADMIN": Role(id=1, name="ADMIN", description="Test administrator"),
        "SELLER": Role(id=2, name="SELLER", description="Test seller"),
        "BUYER": Role(id=3, name="BUYER", description="Test buyer"),
    }
    db.add_all(roles.values())
    db.flush()

    users = [
        User(id=1, username="admin_sarah", email="sarah.chen@bidsmart.io",
             full_name="Test Admin", password_hash=_test_password_hash(),
             role=roles["ADMIN"], status=UserStatus.ACTIVE),
        User(id=3, username="vance_estates", email="marcus.vance@vanceestates.com",
             full_name="Test Seller One", password_hash=_test_password_hash(),
             role=roles["SELLER"], status=UserStatus.ACTIVE),
        User(id=4, username="apex_electronics", email="seller2@example.com",
             full_name="Test Seller Two", password_hash=_test_password_hash(),
             role=roles["SELLER"], status=UserStatus.ACTIVE),
        User(id=8, username="elena_r", email="elena.rostova@gmail.com",
             full_name="Test Buyer One", password_hash=_test_password_hash(),
             role=roles["BUYER"], status=UserStatus.ACTIVE),
        User(id=9, username="david_k", email="buyer2@example.com",
             full_name="Test Buyer Two", password_hash=_test_password_hash(),
             role=roles["BUYER"], status=UserStatus.ACTIVE),
        User(id=10, username="collector_dan", email="collector.dan@example.com",
             full_name="Test Buyer Ten", password_hash=_test_password_hash(),
             role=roles["BUYER"], status=UserStatus.ACTIVE),
    ]
    users.extend(
        User(
            id=user_id,
            username=f"fixture_user_{user_id}",
            email=f"fixture.user.{user_id}@example.com",
            full_name=f"Fixture User {user_id}",
            password_hash=_test_password_hash(),
            role=roles["BUYER"] if user_id % 2 else roles["SELLER"],
            status=UserStatus.ACTIVE,
        )
        for user_id in range(11, 37)
    )
    db.add_all(users)
    db.flush()
    db.add_all(
        SellerPaymentProfile(
            seller_id=user.id,
            setup_mode=SellerPaymentSetupMode.DEMO_SIMULATED,
            status=SellerPaymentSetupStatus.DEMO_COMPLETED,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        for user in users
        if user.role is roles["SELLER"]
    )

    categories = [        Category(id=1, name="Electronics & Computing", slug="electronics-computing", icon_name="Cpu"),
        Category(id=2, name="Fine Art & Antiques", slug="fine-art-antiques", icon_name="Palette"),
        Category(id=3, name="Collectibles", slug="collectibles", icon_name="Tag"),
        Category(id=4, name="Jewelry & Watches", slug="jewelry-watches", icon_name="Watch"),
        Category(id=5, name="Coins", slug="coins", icon_name="Coins"),
        Category(id=6, name="Home & Decor", slug="home-decor", icon_name="Home"),
    ]
    db.add_all(categories)
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for auction_id in range(1, 41):
        seller_id = (
            3
            if auction_id == 14
            else 4
            if auction_id == 16
            else 3
            if auction_id % 2 == 0
            else 4
        )
        category_id = (1, 3, 5)[(auction_id - 1) % 3]
        product = Product(
            id=auction_id,
            seller_id=seller_id,
            category_id=category_id,
            title=("Macintosh test product" if auction_id == 1 else f"Seeded test product {auction_id}"),
            description=f"Isolated API test product {auction_id}",
            condition_status=(
                ProductCondition.NEW if auction_id % 2 else ProductCondition.USED
            ),
            image_url=f"https://example.test/products/{auction_id}.jpg",
        )
        db.add(product)
    db.flush()

    completed_auction_ids = set(range(16, 34))
    for auction_id in range(1, 41):
        is_completed = auction_id in completed_auction_ids
        is_scheduled = auction_id == 15
        is_active = not is_completed and not is_scheduled
        winning_amount = 550 if auction_id == 1 else 200 + auction_id
        auction = Auction(
            id=auction_id,
            product_id=auction_id,
            starting_price=(
                15000 if auction_id == 14 else 100 if auction_id == 1 else 50
            ),
            current_highest_bid=winning_amount if auction_id == 1 or is_completed else None,
            reserve_price=20000 if auction_id == 14 else None,
            minimum_increment=25 if auction_id == 1 else 5,
            start_time=(
                now + timedelta(days=1)
                if is_scheduled
                else now - timedelta(days=2 if is_completed else 0, hours=1)
            ),
            end_time=(
                now + timedelta(days=2)
                if is_scheduled
                else now - timedelta(days=1)
                if is_completed
                else now + timedelta(days=1)
            ),
            status=(
                AuctionStatus.COMPLETED if is_completed
                else AuctionStatus.ACTIVE if is_active
                else AuctionStatus.SCHEDULED
            ),
            winner_id=9 if auction_id == 1 or is_completed else None,
            total_bids=2 if auction_id == 1 else 1 if is_completed else 0,
        )
        db.add(auction)
    db.flush()

    bid_id = 1
    bid_specs = [(1, 8, 500, False), (1, 9, 550, True)]
    for auction_id in sorted(completed_auction_ids):
        amount = 200 + auction_id
        bid_specs.append((auction_id, 9, amount, True))
        bid_specs.extend(
            (auction_id, 8 if index % 2 else 9, amount - index, False)
            for index in range(1, 20)
        )

    winning_bid_ids = {}
    for auction_id, bidder_id, amount, is_winner in bid_specs:
        bid = Bid(
            id=bid_id,
            auction_id=auction_id,
            bidder_id=bidder_id,
            bid_amount=amount,
            is_winning_bid=is_winner,
            is_flagged_anomaly=False,
            ip_address="127.0.0.1",
        )
        db.add(bid)
        if is_winner:
            winning_bid_ids[auction_id] = bid_id
        bid_id += 1
    db.flush()

    for auction_id, winning_bid_id in winning_bid_ids.items():
        db.query(Auction).filter(Auction.id == auction_id).update(
            {Auction.winning_bid_id: winning_bid_id},
            synchronize_session=False,
        )

    db.add_all(
        Transaction(
            auction_id=auction_id,
            buyer_id=9,
            seller_id=3 if auction_id == 14 else 4 if auction_id == 16 else (3 if auction_id % 2 == 0 else 4),
            amount=200 + auction_id,
            settlement_type=SettlementType.SIMULATED_DEMO,
            payment_status=PaymentStatus.SETTLEMENT_COMPLETED_DEMO,
            payment_reference=f"FIXTURE-TX-{auction_id}",
            settled_at=now,
        )
        for auction_id in sorted(completed_auction_ids)
    )
    db.add_all(
        Watchlist(user_id=8 if index <= 18 else 9, auction_id=index)
        for index in range(1, 36)
    )
    db.add_all(
        Notification(
            user_id=8 if index % 2 else 9,
            type="SYSTEM",
            title=f"Fixture notification {index}",
            message="Isolated test notification.",
        )
        for index in range(1, 14)
    )
    db.add_all(
        AuditLog(
            user_id=1,
            action=f"FIXTURE_ACTION_{index}",
            entity_type="FIXTURE",
            entity_id=index,
        )
        for index in range(1, 9)
    )
    db.commit()


@pytest.fixture(scope="session")
def isolated_database(tmp_path_factory):
    """A temporary file-backed SQLite database shared by the test app only."""
    database_directory = tempfile.TemporaryDirectory(
        prefix="bidsmart-pytest-",
        dir=str(tmp_path_factory.getbasetemp()),
    )
    database_path = str(Path(database_directory.name) / "bidsmart_test.sqlite3")
    engine = create_engine(
        URL.create("sqlite", database=database_path),
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield {"engine": engine, "session_factory": factory}
    finally:
        engine.dispose()
        database_directory.cleanup()


@pytest.fixture(autouse=True)
def clean_test_artifacts(request):
    """Reset only the disposable SQLite database before each ordinary test."""
    if request.node.get_closest_marker("mysql"):
        yield
        return

    isolated_database = request.getfixturevalue("isolated_database")
    engine = isolated_database["engine"]
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    with isolated_database["session_factory"]() as db:
        _seed_marketplace(db)
    yield


def _sqlite_health(isolated_database) -> dict:
    """Return real health telemetry for the isolated SQLite test database."""
    started = time.perf_counter()
    with isolated_database["engine"].connect() as connection:
        version = connection.execute(text("SELECT sqlite_version()")).scalar_one()
    pool = isolated_database["engine"].pool
    return {
        "status": "connected",
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "server_version": f"SQLite {version}",
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "overflow": pool.overflow(),
    }


@pytest.fixture()
def client(isolated_database, monkeypatch):
    """Serve API requests from SQLite without running the production lifespan."""
    from app.api.v1.endpoints import health

    def override_get_db():
        with isolated_database["session_factory"]() as db:
            yield db

    @asynccontextmanager
    async def no_application_lifespan(_app):
        yield

    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    monkeypatch.setattr(app.router, "lifespan_context", no_application_lifespan)
    monkeypatch.setattr(
        health,
        "check_db_health",
        lambda: _sqlite_health(isolated_database),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db(isolated_database):
    """Direct test session bound to the same isolated database as the API client."""
    with isolated_database["session_factory"]() as session:
        yield session


@pytest.fixture()
def auth_tokens(client):
    """Authentication tokens for seeded administrator, sellers, and buyer."""
    def login(username: str) -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"username_or_email": username, "password": TEST_PASSWORD},
        )
        response.raise_for_status()
        return response.json()["access_token"]

    return {
        "admin": login("admin_sarah"),
        "s1": login("vance_estates"),
        "s2": login("apex_electronics"),
        "buyer": login("elena_r"),
        "b1": login("elena_r"),
        "b2": login("david_k"),
    }


@pytest.fixture()
def test_users(auth_tokens):
    return auth_tokens


@pytest.fixture()
def mysql_concurrency():
    """Opt-in fixture for the stored-procedure concurrency test on local MySQL."""
    database_url = os.environ.get("BIDSMART_TEST_MYSQL_URL")
    write_opt_in = os.environ.get("BIDSMART_ALLOW_MYSQL_TEST_WRITES")
    if not database_url or write_opt_in != MYSQL_TEST_WRITE_OPT_IN:
        pytest.fail(
            "MySQL concurrency test requires BIDSMART_TEST_MYSQL_URL and "
            "BIDSMART_ALLOW_MYSQL_TEST_WRITES with the documented disposable-DB opt-in."
        )

    try:
        parsed_url = make_url(database_url)
        application_url = make_url(settings.SQLALCHEMY_DATABASE_URI)
    except Exception as exc:
        pytest.fail(
            "Could not safely establish database identities for the MySQL "
            f"concurrency test ({type(exc).__name__})."
        )

    def normalized_host(host):
        value = (host or "").strip().lower()
        return "loopback" if value in {"localhost", "127.0.0.1", "::1"} else value

    if (
        application_url.drivername != "mysql+pymysql"
        or not application_url.host
        or not application_url.database
    ):
        pytest.fail(
            "Could not safely establish the configured application database identity; "
            "the MySQL concurrency test will not connect."
        )

    application_identity = (
        application_url.drivername,
        normalized_host(application_url.host),
        application_url.port or 3306,
        application_url.database.casefold(),
    )
    test_identity = (
        parsed_url.drivername,
        normalized_host(parsed_url.host),
        parsed_url.port or 3306,
        (parsed_url.database or "").casefold(),
    )
    if (
        parsed_url.drivername != "mysql+pymysql"
        or normalized_host(parsed_url.host) != "loopback"
        or parsed_url.database != MYSQL_TEST_DATABASE
        or not parsed_url.username
        or test_identity == application_identity
        or test_identity[3] == application_identity[3]
    ):
        pytest.fail(
            "MySQL concurrency tests require a separate localhost database named "
            f"{MYSQL_TEST_DATABASE}; it must not match the configured application "
            "database. Application database settings are never used."
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
        future=True,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = None
    seed_ids = None
    previous_lifespan = app.router.lifespan_context
    previous_overrides = dict(app.dependency_overrides)
    from app.api.v1.endpoints import health
    previous_health_checker = health.check_db_health
    try:
        with engine.connect() as connection:
            actual_database = connection.execute(text("SELECT DATABASE()")).scalar_one()
            routine_exists = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.ROUTINES "
                    "WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_NAME = 'sp_place_bid'"
                )
            ).scalar_one()
        if actual_database != MYSQL_TEST_DATABASE or not routine_exists:
            pytest.fail(
                "Dedicated MySQL database identity or sp_place_bid routine validation failed."
            )

        @asynccontextmanager
        async def no_application_lifespan(_app):
            yield

        def override_get_db():
            with session_factory() as request_db:
                yield request_db

        def mysql_health():
            started = time.perf_counter()
            with engine.connect() as connection:
                version = connection.execute(text("SELECT VERSION()")).scalar_one()
            pool = engine.pool
            return {
                "status": "connected",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "server_version": version,
                "pool_size": pool.size(),
                "checked_in_connections": pool.checkedin(),
                "checked_out_connections": pool.checkedout(),
                "overflow": pool.overflow(),
            }

        app.dependency_overrides[get_db] = override_get_db
        app.router.lifespan_context = no_application_lifespan
        health.check_db_health = mysql_health

        db = session_factory()
        role = db.query(Role).filter(Role.name == "SELLER").first()
        buyer_role = db.query(Role).filter(Role.name == "BUYER").first()
        created_roles = []
        if role is None:
            role = Role(name="SELLER", description="Disposable concurrency test seller")
            db.add(role)
            created_roles.append(role)
        if buyer_role is None:
            buyer_role = Role(name="BUYER", description="Disposable concurrency test buyer")
            db.add(buyer_role)
            created_roles.append(buyer_role)
        db.flush()
        suffix = uuid4().hex
        seller = User(
            username=f"pytest_seller_{suffix}",
            email=f"pytest_seller_{suffix}@example.com",
            full_name="Concurrency Test Seller",
            password_hash="not-used",
            role=role,
            status=UserStatus.ACTIVE,
        )
        buyers = [
            User(
                username=f"pytest_buyer_{suffix}_{index}",
                email=f"pytest_buyer_{suffix}_{index}@example.com",
                full_name=f"Concurrency Test Buyer {index}",
                password_hash="not-used",
                role=buyer_role,
                status=UserStatus.ACTIVE,
            )
            for index in range(2)
        ]
        category = Category(
            name=f"Pytest Concurrency {suffix}",
            slug=f"pytest-concurrency-{suffix}",
            icon_name="Tag",
        )
        db.add_all([seller, *buyers, category])
        db.commit()
        seed_ids = {
            "user_ids": [seller.id, *(buyer.id for buyer in buyers)],
            "role_ids": [role.id for role in created_roles],
            "category_id": category.id,
            "seller_id": seller.id,
        }
        tokens = {
            "s1": create_access_token(seller.id, seller.username, "SELLER"),
            "b1": create_access_token(buyers[0].id, buyers[0].username, "BUYER"),
            "b2": create_access_token(buyers[1].id, buyers[1].username, "BUYER"),
        }
        with TestClient(app) as test_client:
            yield {
                "client": test_client,
                "db": db,
                "tokens": tokens,
                "category_id": category.id,
                "seed_ids": seed_ids,
                "session_factory": session_factory,
                "engine": engine,
            }
    finally:
        if db is not None:
            if seed_ids:
                try:
                    product_ids = [
                        product_id
                        for (product_id,) in db.query(Product.id).filter(
                            Product.category_id == seed_ids["category_id"]
                        ).all()
                    ]
                    auction_ids = (
                        [
                            auction_id
                            for (auction_id,) in db.query(Auction.id).filter(
                                Auction.product_id.in_(product_ids)
                            ).all()
                        ]
                        if product_ids
                        else []
                    )
                    transaction_ids = (
                        [
                            transaction_id
                            for (transaction_id,) in db.query(Transaction.id).filter(
                                Transaction.auction_id.in_(auction_ids)
                            ).all()
                        ]
                        if auction_ids
                        else []
                    )
                    user_ids = seed_ids["user_ids"]
                    if transaction_ids:
                        db.query(PaymentAttempt).filter(
                            PaymentAttempt.transaction_id.in_(transaction_ids)
                        ).delete(synchronize_session=False)
                        db.query(Transaction).filter(
                            Transaction.id.in_(transaction_ids)
                        ).delete(synchronize_session=False)
                    if auction_ids:
                        db.query(Watchlist).filter(
                            Watchlist.auction_id.in_(auction_ids)
                        ).delete(synchronize_session=False)
                        db.query(Bid).filter(
                            Bid.auction_id.in_(auction_ids)
                        ).delete(synchronize_session=False)
                        db.query(AuditLog).filter(
                            AuditLog.entity_type == "AUCTION",
                            AuditLog.entity_id.in_(auction_ids),
                        ).delete(synchronize_session=False)
                        db.query(Auction).filter(
                            Auction.id.in_(auction_ids)
                        ).delete(synchronize_session=False)
                    db.query(Notification).filter(
                        Notification.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    db.query(AuditLog).filter(
                        AuditLog.user_id.in_(user_ids)
                    ).delete(synchronize_session=False)
                    if product_ids:
                        db.query(Product).filter(
                            Product.id.in_(product_ids)
                        ).delete(synchronize_session=False)
                    db.query(Category).filter(
                        Category.id == seed_ids["category_id"]
                    ).delete(synchronize_session=False)
                    db.query(User).filter(User.id.in_(seed_ids["user_ids"])).delete(
                        synchronize_session=False
                    )
                    if seed_ids["role_ids"]:
                        db.query(Role).filter(
                            Role.id.in_(seed_ids["role_ids"])
                        ).delete(synchronize_session=False)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            db.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        app.router.lifespan_context = previous_lifespan
        health.check_db_health = previous_health_checker
        engine.dispose()
