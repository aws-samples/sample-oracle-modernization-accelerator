
[MySQL 전문가 모드]
함수 Test SQL 수행 실패한 내용을 $APP_TRANSFORM_FOLDER/sqlTestResultFailed.json 에 기록하였음.
이 화일은 $APP_TOOLS_FOLDER/../postTransform/function/genSelectFromXML.py 에 의해 수행된 결과임.
  sqlTestResultFailed.json 화일구조
   - TransformXMLFileName : Test SQL을 만들기 위한 XML
   - Status : Test SQL 수행 결과
   - TestSQL : Function Test SQL
   - SQLErrorMessage : 오류 메세지
   - TransformXMLFile : Test SQL을 만들기 위한 XML-Paht포함 - $TARGET_DBMS_TYPE 용
   - OriginXMLFile : TransformXMLFile의 원래 원본 XML화일 - $SOURCE_DBMS_TYPE 용
sqlTestResultFailed.json에 기록된 오류를 하나씩 검토하여 오류에 대한 후속 조치를 작업지시에 따라 수행할것.

작업.
   $APP_TRANSFORM_FOLDER/sqlTestResultFailed.json 의 내용을 확인 하고 개선작업을 수행 : Test SQL, SQLErrorMessage, Transfrom XML, Origin XML 
    1 실패한 SQL을 Debug 모드로 재수행 : cd $APP_TOOLS_FOLDER/../postTransform/function/ && python3 ./genSelectFromXML.py TransformXMLFile --debug
    2 TransformXMLFile 이 잘못 변환 되었는지, Test를 위한 Test SQL이 잘못되었는지 명확히 판단 할것
        예. Transform XML의 변환 로직이 잘못되어서 Test SQL 생성 시 문법 오류가 발생하는 것입니다. genSelectFromXML 프로그램이 문제가 아니라, 변환된 XML 자체에 MySQL 문법 오류가 있는 상황입니다.
    3 사용자가 어느 영역을 검토할지 선택하게 할것.
    
        Case1. Test SQL 프로그램 검증
          - Test SQL을 위한 Function을 추출하는 로직이 원본 XML에서 의도대로 추출된것인지 확인.
          - 변환 순서에 따른 결과를 추적
          - 프로그램 수정 범위를 제언
        Case2. Transform XML 검토
            - 추출은 잘되었는데 Transform XML이 문법이 잘못되었거나 함수 사용법이 틀린경우 가 있는지 확인할것.
            - 필요하다면 Origin XML을 검토 하여 Source to Target 변환이 올바른지 사전 검토
                - OriginXMLFile은 TransformXMLFile에서 transform -> extract, tgt -> src 인 화일임
                - OriginXMLFile을 검토하여 OriginXMLFile에서 TransformXMLFile로 전환이 잘 되었는지, 의도가 유지되었는지 검토 
            - 변환 오류라고 판단 되었을때 TransformXMLFile의 수정계획을 제언

    4 선택 사항에 따라서 어떻게 수정해야하는지 계획 수립
        Test SQL 프로그램 수정시
                - 변수 치환, 패턴 추출 문제에 대한 해결안 제시 및 프로그램 수정
                - 파서를 우선적으로 활용할것.
                - 변경 적용시 순서에 대해서 고민할것. 선행,후행 변환룰이 중요함
                - 수정 완료후 Test SQL을 신규 생성 및 재 Test 수행 : debug모드
        TransformXMLFile 수정
                - 수정 완료후 Test SQL을 신규 생성 및 재 Test 수행 : debug모드
    5 오류가 없다면 sqlTestResultFailed.json의 항목을 삭제 할것.
    6 전체 리스트의 각 항목에 대해서 수행
주의사항
   - 오류유형이 같더라도 XML 내의 SQL은 독립적이기 때문에 화일 하나씩 처리하는것을 원칙으로 한다. - 절대 규칙임.
   - TransformXMLFile을 수정하는 경우에는 XML Tag에 유의.
   - XML Tag는 절대 건드리지 말것. 패턴 방식으로 수정하려면 반드시 어떤 작업인지 알려주고, 승인 받을것.
   - 비슷한 오류 유형을 패턴으로 찾는것은 허용하지만, 변경은 각 변경단위 별로 승인을 꼭 받아야 함
   - TransformXMLFile을 수정하는 경우, 같은 기능이 아니고 유사한 기능으로 변경하는 경우로 판단된다면 SQL Style 주석을 추가할것 : TODO:기능동질성확인(수정내용)
   - 동일 결과가 나오는 수정 이라면 그냥 수정 할것.
   - 변환이 안되는 $SOURCE_DBMS_TYPE의 기능이 남아있다면, 현재 그 기능 부분을 주석처리하고 NULL 컬럼으로 대체할것. 그리고 SQL Style 참조 주석을 추가할것 : TODO:추가 수정 필요. (수정 필요내용)
   - TransformXMLFile은 수정전에 동일 위치에 꼭 백업을 받을것


