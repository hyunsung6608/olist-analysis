-- Olist 분석용 테이블 생성 (MySQL 8.0, utf8mb4)
-- 부모 테이블부터 순서대로 생성한다. create_schema.py --reset은 이 파일의 역순으로 테이블을 지운다.
-- 컬럼 이름은 원본 CSV를 그대로 따른다(원본 오타 product_name_lenght 등 포함).
-- 콜레이션은 지정하지 않고 DB 기본값을 따른다.

-- 카테고리 번역표 (products와 FK 없음: 번역표에 없는 카테고리 2개, 빈 카테고리 610건)
CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name         VARCHAR(64) NOT NULL COMMENT '카테고리명(포르투갈어)',
    product_category_name_english VARCHAR(64) NOT NULL COMMENT '카테고리명(영어)',
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='상품 카테고리 포르투갈어-영어 번역표';

CREATE TABLE IF NOT EXISTS customers (
    customer_id              CHAR(32)    NOT NULL COMMENT '주문 단위 고객 ID (주문마다 새로 발급)',
    customer_unique_id       CHAR(32)    NOT NULL COMMENT '실제 고객 ID (재구매 분석 기준)',
    customer_zip_code_prefix CHAR(5)     NOT NULL COMMENT '우편번호 앞 5자리 (앞자리 0 보존)',
    customer_city            VARCHAR(64) NOT NULL COMMENT '도시',
    customer_state           CHAR(2)     NOT NULL COMMENT '주 약어',
    PRIMARY KEY (customer_id),
    INDEX idx_customers_unique_id (customer_unique_id),
    INDEX idx_customers_zip (customer_zip_code_prefix),
    INDEX idx_customers_state (customer_state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='고객 (주문 단위 customer_id 기준)';

CREATE TABLE IF NOT EXISTS sellers (
    seller_id              CHAR(32)    NOT NULL COMMENT '판매자 ID',
    seller_zip_code_prefix CHAR(5)     NOT NULL COMMENT '우편번호 앞 5자리 (앞자리 0 보존)',
    seller_city            VARCHAR(64) NOT NULL COMMENT '도시',
    seller_state           CHAR(2)     NOT NULL COMMENT '주 약어',
    PRIMARY KEY (seller_id),
    INDEX idx_sellers_zip (seller_zip_code_prefix),
    INDEX idx_sellers_state (seller_state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='판매자';

CREATE TABLE IF NOT EXISTS products (
    product_id                 CHAR(32)    NOT NULL COMMENT '상품 ID',
    product_category_name      VARCHAR(64) NULL     COMMENT '카테고리명(포르투갈어), 없으면 NULL',
    product_name_lenght        INT         NULL     COMMENT '상품명 길이 (원본 컬럼명 오타 유지)',
    product_description_lenght INT         NULL     COMMENT '상품 설명 길이 (원본 컬럼명 오타 유지)',
    product_photos_qty         INT         NULL     COMMENT '사진 수',
    product_weight_g           INT         NULL     COMMENT '무게(g)',
    product_length_cm          INT         NULL     COMMENT '길이(cm)',
    product_height_cm          INT         NULL     COMMENT '높이(cm)',
    product_width_cm           INT         NULL     COMMENT '너비(cm)',
    PRIMARY KEY (product_id),
    INDEX idx_products_category (product_category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='상품';

CREATE TABLE IF NOT EXISTS orders (
    order_id                      CHAR(32)    NOT NULL COMMENT '주문 ID',
    customer_id                   CHAR(32)    NOT NULL COMMENT '주문 단위 고객 ID',
    order_status                  VARCHAR(20) NOT NULL COMMENT '주문 상태 (delivered, shipped, canceled 등)',
    order_purchase_timestamp      DATETIME    NOT NULL COMMENT '구매 시각',
    order_approved_at             DATETIME    NULL     COMMENT '결제 승인 시각',
    order_delivered_carrier_date  DATETIME    NULL     COMMENT '택배사 인계 시각',
    order_delivered_customer_date DATETIME    NULL     COMMENT '고객 배송 완료 시각',
    order_estimated_delivery_date DATETIME    NOT NULL COMMENT '고객에게 안내한 배송 예정일',
    PRIMARY KEY (order_id),
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_status (order_status),
    INDEX idx_orders_purchase (order_purchase_timestamp),
    INDEX idx_orders_delivered (order_delivered_customer_date),
    INDEX idx_orders_estimated (order_estimated_delivery_date),
    CONSTRAINT fk_orders_customers FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='주문';

CREATE TABLE IF NOT EXISTS order_items (
    order_id            CHAR(32)      NOT NULL COMMENT '주문 ID',
    order_item_id       SMALLINT      NOT NULL COMMENT '주문 내 상품 순번 (1부터)',
    product_id          CHAR(32)      NOT NULL COMMENT '상품 ID',
    seller_id           CHAR(32)      NOT NULL COMMENT '판매자 ID',
    shipping_limit_date DATETIME      NOT NULL COMMENT '판매자 발송 기한',
    price               DECIMAL(10,2) NOT NULL COMMENT '상품 가격(BRL)',
    freight_value       DECIMAL(10,2) NOT NULL COMMENT '배송비(BRL), 같은 주문 상품에 나눠 배분됨',
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_order_items_product (product_id),
    INDEX idx_order_items_seller (seller_id),
    INDEX idx_order_items_shipping_limit (shipping_limit_date),
    CONSTRAINT fk_order_items_orders   FOREIGN KEY (order_id)   REFERENCES orders (order_id),
    CONSTRAINT fk_order_items_products FOREIGN KEY (product_id) REFERENCES products (product_id),
    CONSTRAINT fk_order_items_sellers  FOREIGN KEY (seller_id)  REFERENCES sellers (seller_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='주문 상품 (주문 1건에 여러 행)';

CREATE TABLE IF NOT EXISTS order_payments (
    order_id             CHAR(32)      NOT NULL COMMENT '주문 ID',
    payment_sequential   SMALLINT      NOT NULL COMMENT '주문 내 결제 순번',
    payment_type         VARCHAR(20)   NOT NULL COMMENT '결제 수단 (credit_card, boleto, voucher 등)',
    payment_installments SMALLINT      NOT NULL COMMENT '할부 개월 수',
    payment_value        DECIMAL(10,2) NOT NULL COMMENT '결제 금액(BRL)',
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_order_payments_orders FOREIGN KEY (order_id) REFERENCES orders (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='주문 결제 (주문 1건에 여러 행 가능)';

CREATE TABLE IF NOT EXISTS order_reviews (
    review_id               CHAR(32) NOT NULL COMMENT '리뷰 ID (단독으로는 고유하지 않음)',
    order_id                CHAR(32) NOT NULL COMMENT '주문 ID',
    review_score            TINYINT  NOT NULL COMMENT '평점 1~5',
    review_comment_title    TEXT     NULL     COMMENT '리뷰 제목(포르투갈어)',
    review_comment_message  TEXT     NULL     COMMENT '리뷰 본문(포르투갈어)',
    review_creation_date    DATETIME NOT NULL COMMENT '리뷰 요청 발송일',
    review_answer_timestamp DATETIME NOT NULL COMMENT '리뷰 작성 시각',
    PRIMARY KEY (review_id, order_id),
    INDEX idx_order_reviews_order (order_id),
    INDEX idx_order_reviews_score (review_score),
    INDEX idx_order_reviews_creation (review_creation_date),
    CONSTRAINT fk_order_reviews_orders FOREIGN KEY (order_id) REFERENCES orders (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='주문 리뷰 (review_id와 order_id 조합이 고유)';

-- 위경도 원본 (우편번호당 여러 행, 고객·판매자와 FK 없음)
CREATE TABLE IF NOT EXISTS geolocation (
    id                          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '적재 순번',
    geolocation_zip_code_prefix CHAR(5)     NOT NULL COMMENT '우편번호 앞 5자리',
    geolocation_lat             DOUBLE      NOT NULL COMMENT '위도',
    geolocation_lng             DOUBLE      NOT NULL COMMENT '경도',
    geolocation_city            VARCHAR(64) NOT NULL COMMENT '도시',
    geolocation_state           CHAR(2)     NOT NULL COMMENT '주 약어',
    PRIMARY KEY (id),
    INDEX idx_geolocation_zip (geolocation_zip_code_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='우편번호별 위경도 원본 (우편번호 중복 있음)';

-- 우편번호당 1행 요약 (고객·판매자 우편번호와 조인용, FK 없음)
CREATE TABLE IF NOT EXISTS geolocation_agg (
    zip_code_prefix CHAR(5)     NOT NULL COMMENT '우편번호 앞 5자리',
    lat             DOUBLE      NOT NULL COMMENT '평균 위도',
    lng             DOUBLE      NOT NULL COMMENT '평균 경도',
    city            VARCHAR(64) NOT NULL COMMENT '가장 많이 나온 도시',
    state           CHAR(2)     NOT NULL COMMENT '가장 많이 나온 주',
    n_points        INT         NOT NULL COMMENT '평균에 쓴 원본 행 수',
    PRIMARY KEY (zip_code_prefix),
    INDEX idx_geolocation_agg_state (state)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='우편번호당 평균 위경도와 최빈 도시·주';

-- LLM 리뷰 불만 분류 결과 (data/results/review_complaint_labels.csv, order_reviews와 FK 없음)
CREATE TABLE IF NOT EXISTS review_complaint_labels (
    review_id                CHAR(32)    NOT NULL COMMENT '리뷰 ID (분류 대상은 review_id 기준 중복 제거)',
    DELAY                    TINYINT     NOT NULL COMMENT '배송 지연 (0/1)',
    NOT_RECEIVED             TINYINT     NOT NULL COMMENT '미수령 (0/1)',
    WRONG_MISSING            TINYINT     NOT NULL COMMENT '오배송·누락 (0/1)',
    DAMAGED                  TINYINT     NOT NULL COMMENT '파손·불량 (0/1)',
    NOT_AS_DESCRIBED         TINYINT     NOT NULL COMMENT '설명 불일치 (0/1)',
    LOW_QUALITY              TINYINT     NOT NULL COMMENT '품질 불만 (0/1)',
    SERVICE                  TINYINT     NOT NULL COMMENT '응대·환불 (0/1)',
    SHIPPING_COST            TINYINT     NOT NULL COMMENT '배송비·수령 불편 (0/1)',
    OTHER                    TINYINT     NOT NULL COMMENT '기타 (0/1)',
    UNCLEAR                  TINYINT     NOT NULL COMMENT '판단 불가 (0/1)',
    NO_COMPLAINT             TINYINT     NOT NULL COMMENT '불만 없음 (0/1)',
    primary_label            VARCHAR(20) NOT NULL COMMENT '주 원인 (우선순위 기준 1개)',
    raw_labels               VARCHAR(100) NOT NULL COMMENT '후처리 전 LLM 라벨 (|로 구분)',
    postprocess_rules        VARCHAR(255) NOT NULL DEFAULT '' COMMENT '적용된 후처리 규칙 (|로 구분)',
    flag_rule_c_violation    TINYINT     NOT NULL COMMENT '규칙 C 위반 의심 (부분 미수령+NOT_RECEIVED)',
    flag_exclusive_violation TINYINT     NOT NULL COMMENT '단독 유형 위반 (NO_COMPLAINT·UNCLEAR+다른 유형)',
    model                    VARCHAR(50) NOT NULL COMMENT '분류 모델',
    taxonomy_version         VARCHAR(10) NOT NULL COMMENT '분류 체계 버전',
    prompt_hash              CHAR(12)    NOT NULL COMMENT '프롬프트 해시',
    PRIMARY KEY (review_id),
    INDEX idx_rcl_primary_label (primary_label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='LLM 리뷰 불만 유형 분류 결과 (1~3점·텍스트 있는 리뷰)';
